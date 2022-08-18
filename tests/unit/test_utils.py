# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import signal
import platform
import pytest
import subprocess
import os

import botocore.model

from awscli.testutils import unittest, skip_if_windows, mock
from awscli.utils import (
    split_on_commas, ignore_ctrl_c, find_service_and_method_in_event_name,
    is_document_type, is_document_type_container, is_streaming_blob_type,
    is_tagged_union_type, operation_uses_document_types, ShapeWalker,
    ShapeRecordingVisitor, OutputStreamFactory
)


@pytest.fixture()
def argument_model():
    return botocore.model.Shape('argument', {'type': 'string'})


class TestCSVSplit(unittest.TestCase):

    def test_normal_csv_split(self):
        self.assertEqual(split_on_commas('foo,bar,baz'),
                         ['foo', 'bar', 'baz'])

    def test_quote_split(self):
        self.assertEqual(split_on_commas('foo,"bar",baz'),
                         ['foo', 'bar', 'baz'])

    def test_inner_quote_split(self):
        self.assertEqual(split_on_commas('foo,bar="1,2,3",baz'),
                         ['foo', 'bar=1,2,3', 'baz'])

    def test_single_quote(self):
        self.assertEqual(split_on_commas("foo,bar='1,2,3',baz"),
                         ['foo', 'bar=1,2,3', 'baz'])

    def test_mixing_double_single_quotes(self):
        self.assertEqual(split_on_commas("""foo,bar="1,'2',3",baz"""),
                         ['foo', "bar=1,'2',3", 'baz'])

    def test_mixing_double_single_quotes_before_first_comma(self):
        self.assertEqual(split_on_commas("""foo,bar="1','2',3",baz"""),
                         ['foo', "bar=1','2',3", 'baz'])

    def test_inner_quote_split_with_equals(self):
        self.assertEqual(split_on_commas('foo,bar="Foo:80/bar?a=b",baz'),
                         ['foo', 'bar=Foo:80/bar?a=b', 'baz'])

    def test_single_quoted_inner_value_with_no_commas(self):
        self.assertEqual(split_on_commas("foo,bar='BAR',baz"),
                         ['foo', 'bar=BAR', 'baz'])

    def test_escape_quotes(self):
        self.assertEqual(split_on_commas('foo,bar=1\,2\,3,baz'),
                         ['foo', 'bar=1,2,3', 'baz'])

    def test_no_commas(self):
        self.assertEqual(split_on_commas('foo'), ['foo'])

    def test_trailing_commas(self):
        self.assertEqual(split_on_commas('foo,'), ['foo', ''])

    def test_escape_backslash(self):
        self.assertEqual(split_on_commas('foo,bar\\\\,baz\\\\,qux'),
                         ['foo', 'bar\\', 'baz\\', 'qux'])

    def test_square_brackets(self):
        self.assertEqual(split_on_commas('foo,bar=["a=b",\'2\',c=d],baz'),
                         ['foo', 'bar=a=b,2,c=d', 'baz'])

    def test_quoted_square_brackets(self):
        self.assertEqual(split_on_commas('foo,bar="[blah]",c=d],baz'),
                         ['foo', 'bar=[blah]', 'c=d]', 'baz'])

    def test_missing_bracket(self):
        self.assertEqual(split_on_commas('foo,bar=[a,baz'),
                         ['foo', 'bar=[a', 'baz'])

    def test_missing_bracket2(self):
        self.assertEqual(split_on_commas('foo,bar=a],baz'),
                         ['foo', 'bar=a]', 'baz'])

    def test_bracket_in_middle(self):
        self.assertEqual(split_on_commas('foo,bar=a[b][c],baz'),
                         ['foo', 'bar=a[b][c]', 'baz'])

    def test_end_bracket_in_value(self):
        self.assertEqual(split_on_commas('foo,bar=[foo,*[biz]*,baz]'),
                         ['foo', 'bar=foo,*[biz]*,baz'])


@skip_if_windows("Ctrl-C not supported on windows.")
class TestIgnoreCtrlC(unittest.TestCase):
    def test_ctrl_c_is_ignored(self):
        with ignore_ctrl_c():
            # Should have the noop signal handler installed.
            self.assertEqual(signal.getsignal(signal.SIGINT), signal.SIG_IGN)
            # And if we actually try to sigint ourselves, an exception
            # should not propagate.
            os.kill(os.getpid(), signal.SIGINT)


class TestFindServiceAndOperationNameFromEvent(unittest.TestCase):
    def test_finds_service_and_operation_name(self):
        event_name = "foo.bar.baz"
        service, operation = find_service_and_method_in_event_name(event_name)
        self.assertEqual(service, "bar")
        self.assertEqual(operation, "baz")

    def test_returns_none_if_event_is_too_short(self):
        event_name = "foo.bar"
        service, operation = find_service_and_method_in_event_name(event_name)
        self.assertEqual(service, "bar")
        self.assertIs(operation, None)

        event_name = "foo"
        service, operation = find_service_and_method_in_event_name(event_name)
        self.assertIs(service, None)
        self.assertIs(operation, None)


class MockProcess(object):
    @property
    def stdin(self):
        raise IOError('broken pipe')

    def communicate(self):
        pass


class TestOutputStreamFactory(unittest.TestCase):
    def setUp(self):
        self.popen = mock.Mock(subprocess.Popen)
        self.stream_factory = OutputStreamFactory(self.popen)

    @mock.patch('awscli.utils.get_popen_kwargs_for_pager_cmd')
    def test_pager(self, mock_get_popen_pager):
        mock_get_popen_pager.return_value = {
                'args': ['mypager', '--option']
        }
        with self.stream_factory.get_pager_stream():
            mock_get_popen_pager.assert_called_with(None)
            self.assertEqual(
                self.popen.call_args_list,
                [mock.call(
                    args=['mypager', '--option'],
                    stdin=subprocess.PIPE)]
            )

    @mock.patch('awscli.utils.get_popen_kwargs_for_pager_cmd')
    def test_env_configured_pager(self, mock_get_popen_pager):
        mock_get_popen_pager.return_value = {
            'args': ['mypager', '--option']
        }
        with self.stream_factory.get_pager_stream('mypager --option'):
            mock_get_popen_pager.assert_called_with('mypager --option')
            self.assertEqual(
                self.popen.call_args_list,
                [mock.call(
                    args=['mypager', '--option'],
                    stdin=subprocess.PIPE)]
            )

    @mock.patch('awscli.utils.get_popen_kwargs_for_pager_cmd')
    def test_pager_using_shell(self, mock_get_popen_pager):
        mock_get_popen_pager.return_value = {
            'args': 'mypager --option', 'shell': True
        }
        with self.stream_factory.get_pager_stream():
            mock_get_popen_pager.assert_called_with(None)
            self.assertEqual(
                self.popen.call_args_list,
                [mock.call(
                    args='mypager --option',
                    stdin=subprocess.PIPE,
                    shell=True)]
            )

    def test_exit_of_context_manager_for_pager(self):
        with self.stream_factory.get_pager_stream():
            pass
        returned_process = self.popen.return_value
        self.assertTrue(returned_process.communicate.called)

    @mock.patch('awscli.utils.get_binary_stdout')
    def test_stdout(self, mock_binary_out):
        with self.stream_factory.get_stdout_stream():
            self.assertTrue(mock_binary_out.called)

    def test_can_silence_io_error_from_pager(self):
        self.popen.return_value = MockProcess()
        try:
            # RuntimeError is caught here since a runtime error is raised
            # when an IOError is raised before the context manager yields.
            # If we ignore it like this we will actually see the IOError.
            with self.assertRaises(RuntimeError):
                with self.stream_factory.get_pager_stream():
                    pass
        except IOError:
            self.fail('Should not raise IOError')


class BaseShapeTest(unittest.TestCase):
    def setUp(self):
        self.shapes = {}

    def get_shape_model(self, shape_name):
        shape_model = self.shapes[shape_name]
        resolver = botocore.model.ShapeResolver(self.shapes)
        shape_cls = resolver.SHAPE_CLASSES.get(
            shape_model['type'], botocore.model.Shape
        )
        return shape_cls(shape_name, shape_model, resolver)

    def get_doc_type_shape_definition(self):
        return {
            'type': 'structure',
            'members': {},
            'document': True
        }


class TestIsDocumentType(BaseShapeTest):
    def test_is_document_type(self):
        self.shapes['DocStructure'] = self.get_doc_type_shape_definition()
        self.assertTrue(is_document_type(self.get_shape_model('DocStructure')))

    def test_is_not_document_type_if_missing_document_trait(self):
        self.shapes['NonDocStructure'] = {
            'type': 'structure',
            'members': {},
        }
        self.assertFalse(
            is_document_type(self.get_shape_model('NonDocStructure'))
        )

    def test_is_not_document_type_if_not_structure(self):
        self.shapes['String'] = {'type': 'string'}
        self.assertFalse(is_document_type(self.get_shape_model('String')))


class TestIsDocumentTypeContainer(BaseShapeTest):
    def test_is_document_type_container_for_doc_type(self):
        self.shapes['DocStructure'] = self.get_doc_type_shape_definition()
        self.assertTrue(
            is_document_type_container(self.get_shape_model('DocStructure'))
        )

    def test_is_not_document_type_container_if_missing_document_trait(self):
        self.shapes['NonDocStructure'] = {
            'type': 'structure',
            'members': {},
        }
        self.assertFalse(
            is_document_type_container(self.get_shape_model('NonDocStructure'))
        )

    def test_is_not_document_type_container_if_not_scalar(self):
        self.shapes['String'] = {'type': 'string'}
        self.assertFalse(
            is_document_type_container(self.get_shape_model('String')))

    def test_is_document_type_container_if_list_member(self):
        self.shapes['ListOfDocTypes'] = {
            'type': 'list',
            'member': {'shape': 'DocType'}
        }
        self.shapes['DocType'] = self.get_doc_type_shape_definition()
        self.assertTrue(
            is_document_type_container(self.get_shape_model('ListOfDocTypes'))
        )

    def test_is_document_type_container_if_map_value(self):
        self.shapes['MapOfDocTypes'] = {
            'type': 'map',
            'key': {'shape': 'String'},
            'value': {'shape': 'DocType'}
        }
        self.shapes['DocType'] = self.get_doc_type_shape_definition()
        self.shapes['String'] = {'type': 'string'}
        self.assertTrue(
            is_document_type_container(self.get_shape_model('MapOfDocTypes'))
        )

    def test_is_document_type_container_if_nested_list_member(self):
        self.shapes['NestedListsOfDocTypes'] = {
            'type': 'list',
            'member': {'shape': 'ListOfDocTypes'}
        }
        self.shapes['ListOfDocTypes'] = {
            'type': 'list',
            'member': {'shape': 'DocType'}
        }
        self.shapes['DocType'] = self.get_doc_type_shape_definition()
        self.assertTrue(
            is_document_type_container(
                self.get_shape_model('NestedListsOfDocTypes')
            )
        )


class TestOperationUsesDocumentTypes(BaseShapeTest):
    def setUp(self):
        super(TestOperationUsesDocumentTypes, self).setUp()
        self.input_shape_definition = {
            'type': 'structure',
            'members': {}
        }
        self.shapes['Input'] = self.input_shape_definition
        self.output_shape_definition = {
            'type': 'structure',
            'members': {}
        }
        self.shapes['Output'] = self.output_shape_definition
        self.operation_definition = {
            'input': {'shape': 'Input'},
            'output': {'shape': 'Output'}
        }
        self.service_model = botocore.model.ServiceModel(
            {
                'operations': {'DescribeResource': self.operation_definition},
                'shapes': self.shapes
            }
        )
        self.operation_model = self.service_model.operation_model(
            'DescribeResource')

    def test_operation_uses_document_types_if_doc_type_in_input(self):
        self.shapes['DocType'] = self.get_doc_type_shape_definition()
        self.input_shape_definition['members']['DocType'] = {
            'shape': 'DocType'}
        self.assertTrue(operation_uses_document_types(self.operation_model))

    def test_operation_uses_document_types_if_doc_type_in_output(self):
        self.shapes['DocType'] = self.get_doc_type_shape_definition()
        self.output_shape_definition['members']['DocType'] = {
            'shape': 'DocType'}
        self.assertTrue(operation_uses_document_types(self.operation_model))

    def test_operation_uses_document_types_is_false_when_no_doc_types(self):
        self.assertFalse(operation_uses_document_types(self.operation_model))


class TestShapeWalker(BaseShapeTest):
    def setUp(self):
        super(TestShapeWalker, self).setUp()
        self.walker = ShapeWalker()
        self.visitor = ShapeRecordingVisitor()

    def assert_visited_shapes(self, expected_shape_names):
        self.assertEqual(
            expected_shape_names,
            [shape.name for shape in self.visitor.visited]
        )

    def test_walk_scalar(self):
        self.shapes['String'] = {'type': 'string'}
        self.walker.walk(self.get_shape_model('String'), self.visitor)
        self.assert_visited_shapes(['String'])

    def test_walk_structure(self):
        self.shapes['Structure'] = {
            'type': 'structure',
            'members': {
                'String1': {'shape': 'String'},
                'String2': {'shape': 'String'}
            }
        }
        self.shapes['String'] = {'type': 'string'}
        self.walker.walk(self.get_shape_model('Structure'), self.visitor)
        self.assert_visited_shapes(['Structure', 'String', 'String'])

    def test_walk_list(self):
        self.shapes['List'] = {
            'type': 'list',
            'member': {'shape': 'String'}
        }
        self.shapes['String'] = {'type': 'string'}
        self.walker.walk(self.get_shape_model('List'), self.visitor)
        self.assert_visited_shapes(['List', 'String'])

    def test_walk_map(self):
        self.shapes['Map'] = {
            'type': 'map',
            'key': {'shape': 'KeyString'},
            'value': {'shape': 'ValueString'}
        }
        self.shapes['KeyString'] = {'type': 'string'}
        self.shapes['ValueString'] = {'type': 'string'}
        self.walker.walk(self.get_shape_model('Map'), self.visitor)
        self.assert_visited_shapes(['Map', 'ValueString'])

    def test_can_escape_recursive_shapes(self):
        self.shapes['Recursive'] = {
            'type': 'structure',
            'members': {
                'Recursive': {'shape': 'Recursive'},
            }
        }
        self.walker.walk(self.get_shape_model('Recursive'), self.visitor)
        self.assert_visited_shapes(['Recursive'])


@pytest.mark.usefixtures('argument_model')
class TestStreamingBlob:
    def test_blob_is_streaming(self, argument_model):
        argument_model.type_name = 'blob'
        argument_model.serialization = {'streaming': True}
        assert is_streaming_blob_type(argument_model)

    def test_blob_is_not_streaming(self, argument_model):
        argument_model.type_name = 'blob'
        argument_model.serialization = {}
        assert not is_streaming_blob_type(argument_model)

    def test_non_blob_is_not_streaming(self, argument_model):
        argument_model.type_name = 'string'
        argument_model.serialization = {}
        assert not is_streaming_blob_type(argument_model)


@pytest.mark.usefixtures('argument_model')
class TestTaggedUnion:
    def test_shape_is_tagged_union(self, argument_model):
        setattr(argument_model, 'is_tagged_union', True)
        assert is_tagged_union_type(argument_model)
    
    def test_shape_is_not_tagged_union(self, argument_model):
        assert not is_tagged_union_type(argument_model)
