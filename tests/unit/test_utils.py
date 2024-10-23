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
import json
import os
import shlex

import botocore
import botocore.model
import botocore.session as session
from botocore.exceptions import ConnectionClosedError, MetadataRetrievalError
from awscli.clidriver import create_clidriver
from awscli.testutils import unittest, skip_if_windows, mock
from awscli.compat import is_windows
from awscli.utils import (
    split_on_commas, ignore_ctrl_c, find_service_and_method_in_event_name,
    is_document_type, is_document_type_container, is_streaming_blob_type,
    is_tagged_union_type, operation_uses_document_types, dump_yaml_to_str,
    ShapeWalker, ShapeRecordingVisitor, OutputStreamFactory, LazyPager,
    add_command_lineage_to_user_agent_extra,
    add_metadata_component_to_user_agent_extra,
)
from awscli.utils import InstanceMetadataRegionFetcher
from awscli.utils import IMDSRegionProvider
from tests import RawResponse

import ruamel.yaml


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
        self.assertEqual(split_on_commas(r'foo,bar=1\,2\,3,baz'),
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
            # should not propogate.
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


class PopenException(Exception):
    pass


class TestOutputStreamFactory(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock(session.Session)
        self.popen = mock.Mock(subprocess.Popen)
        self.environ = {}
        self.stream_factory = OutputStreamFactory(
            session=self.session, popen=self.popen,
            environ=self.environ,
        )
        self.pager = 'mypager --option'
        self.set_session_pager(self.pager)
        self.patch_tty = mock.patch('awscli.utils.is_a_tty')
        self.mock_is_a_tty = self.patch_tty.start()
        self.mock_is_a_tty.return_value = True

    def tearDown(self):
        self.patch_tty.stop()

    def set_session_pager(self, pager):
        self.session.get_component.return_value.\
            get_config_variable.return_value = pager

    def assert_popen_call(self, expected_pager_cmd, **override_args):
        popen_kwargs = {
            'stdin': subprocess.PIPE,
            'env': mock.ANY,
            'universal_newlines': True
        }
        if is_windows:
            popen_kwargs['args'] = expected_pager_cmd
            popen_kwargs['shell'] = True
        else:
            popen_kwargs['args'] = shlex.split(expected_pager_cmd)
        popen_kwargs.update(override_args)
        self.popen.assert_called_with(**popen_kwargs)

    def test_pager(self):
        self.set_session_pager('mypager --option')
        with self.stream_factory.get_pager_stream() as stream:
            stream.write()
            self.assert_popen_call(
                expected_pager_cmd='mypager --option'
            )

    def test_explicit_pager(self):
        self.set_session_pager('sessionpager --option')
        with self.stream_factory.get_pager_stream('mypager --option') as stream:
            stream.write()
            self.assert_popen_call(
                expected_pager_cmd='mypager --option'
            )

    def test_exit_of_context_manager_for_pager(self):
        self.set_session_pager('mypager --option')
        with self.stream_factory.get_pager_stream() as stream:
            stream.write()
        returned_process = self.popen.return_value
        self.assertTrue(returned_process.communicate.called)

    def test_propagates_exception_from_popen(self):
        self.popen.side_effect = PopenException
        with self.assertRaises(PopenException):
            with self.stream_factory.get_pager_stream() as stream:
                stream.write()

    @mock.patch('awscli.utils.get_stdout_text_writer')
    def test_stdout(self, mock_stdout_writer):
        with self.stream_factory.get_stdout_stream() as stream:
            stream.write()
            self.assertTrue(mock_stdout_writer.called)

    def test_can_silence_io_error_from_pager(self):
        self.popen.return_value = MockProcess()
        try:
            with self.stream_factory.get_pager_stream() as stream:
                stream.write()
        except IOError:
            self.fail('Should not raise IOError')

    def test_get_output_stream(self):
        self.set_session_pager('mypager --option')
        with self.stream_factory.get_output_stream() as stream:
            stream.write()
            self.assert_popen_call(
                expected_pager_cmd='mypager --option'
            )

    @mock.patch('awscli.utils.get_stdout_text_writer')
    def test_use_stdout_if_not_tty(self, mock_stdout_writer):
        self.mock_is_a_tty.return_value = False
        with self.stream_factory.get_output_stream() as stream:
            stream.write()
            self.assertTrue(mock_stdout_writer.called)

    @mock.patch('awscli.utils.get_stdout_text_writer')
    def test_use_stdout_if_pager_set_to_empty_string(self, mock_stdout_writer):
        self.set_session_pager('')
        with self.stream_factory.get_output_stream() as stream:
            stream.write()
            self.assertTrue(mock_stdout_writer.called)

    def test_adds_default_less_env_vars(self):
        self.set_session_pager('myless')
        with self.stream_factory.get_output_stream() as stream:
            stream.write()
            self.assert_popen_call(
                expected_pager_cmd='myless',
                env={'LESS': 'FRX'}
            )

    def test_does_not_clobber_less_env_var_if_in_env_vars(self):
        self.set_session_pager('less')
        self.environ['LESS'] = 'S'
        with self.stream_factory.get_output_stream() as stream:
            stream.write()
            self.assert_popen_call(
                expected_pager_cmd='less',
                env={'LESS': 'S'}
            )

    def test_set_less_flags_through_constructor(self):
        self.set_session_pager('less')
        stream_factory = OutputStreamFactory(
            self.session, self.popen, self.environ, default_less_flags='ABC')
        with stream_factory.get_output_stream() as stream:
            stream.write()
            self.assert_popen_call(
                expected_pager_cmd='less',
                env={'LESS': 'ABC'}
            )

    def test_not_create_pager_process_if_not_called(self):
        self.set_session_pager('sessionpager --option')
        with self.stream_factory.get_pager_stream('mypager --option'):
            self.assertEqual(self.popen.call_count, 0)

    def test_create_process_on_stdin_method_call(self):
        self.set_session_pager('less')
        stream_factory = OutputStreamFactory(
            self.session, self.popen, self.environ, default_less_flags='ABC')
        with stream_factory.get_output_stream() as stream:
            self.assertEqual(self.popen.call_count, 0)
            stream.write()
            self.assert_popen_call(
                expected_pager_cmd='less',
                env={'LESS': 'ABC'}
            )

    def test_not_create_process_if_stream_not_created(self):
        self.set_session_pager('less')
        stream_factory = OutputStreamFactory(
            self.session, self.popen, self.environ, default_less_flags='ABC')
        with stream_factory.get_output_stream():
            self.assertEqual(self.popen.call_count, 0)
        self.assertEqual(self.popen.call_count, 0)


class BaseIMDSRegionTest(unittest.TestCase):
    def setUp(self):
        urllib3_session_send = 'botocore.httpsession.URLLib3Session.send'
        self._urllib3_patch = mock.patch(urllib3_session_send)
        self._send = self._urllib3_patch.start()
        self._imds_responses = []
        self._send.side_effect = self.get_imds_response
        self._region = 'us-mars-1a'
        self.environ = {}
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()

    def tearDown(self):
        self._urllib3_patch.stop()
        self.environ_patch.stop()

    def add_imds_response(self, body, status_code=200):
        response = botocore.awsrequest.AWSResponse(
            url='http://169.254.169.254/',
            status_code=status_code,
            headers={},
            raw=RawResponse(body)
        )
        self._imds_responses.append(response)

    def add_get_region_imds_response(self, region=None):
        if region is None:
            region = self._region
        self.add_imds_response(body=region.encode('utf-8'))

    def add_imds_token_response(self):
        self.add_imds_response(status_code=200, body=b'token')

    def add_imds_connection_error(self, exception):
        self._imds_responses.append(exception)

    def get_imds_response(self, request):
        response = self._imds_responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class TestInstanceMetadataRegionFetcher(BaseIMDSRegionTest):
    def test_disabled_by_environment(self):
        env = {'AWS_EC2_METADATA_DISABLED': 'true'}
        fetcher = InstanceMetadataRegionFetcher(env=env)
        result = fetcher.retrieve_region()
        self.assertIsNone(result)
        self._send.assert_not_called()

    def test_disabled_by_environment_mixed_case(self):
        env = {'AWS_EC2_METADATA_DISABLED': 'tRuE'}
        fetcher = InstanceMetadataRegionFetcher(env=env)
        result = fetcher.retrieve_region()
        self.assertIsNone(result)
        self._send.assert_not_called()

    def test_disabling_env_var_not_true(self):
        url = 'https://example.com/'
        env = {'AWS_EC2_METADATA_DISABLED': 'false'}

        self.add_imds_token_response()
        self.add_get_region_imds_response()

        fetcher = InstanceMetadataRegionFetcher(base_url=url, env=env)
        result = fetcher.retrieve_region()

        expected_result = 'us-mars-1'
        self.assertEqual(result, expected_result)

    def test_includes_user_agent_header(self):
        user_agent = 'my-user-agent'
        self.add_imds_token_response()
        self.add_get_region_imds_response()

        InstanceMetadataRegionFetcher(
            user_agent=user_agent).retrieve_region()

        headers = self._send.call_args[0][0].headers
        self.assertEqual(headers['User-Agent'], user_agent)

    def test_non_200_response_for_region_is_retried(self):
        # Response for role name that have a non 200 status code should
        # be retried.
        self.add_imds_token_response()
        self.add_imds_response(
            status_code=429, body=b'{"message": "Slow down"}')
        self.add_get_region_imds_response()
        result = InstanceMetadataRegionFetcher(
            num_attempts=2).retrieve_region()
        expected_result = 'us-mars-1'
        self.assertEqual(result, expected_result)

    def test_empty_response_for_region_is_retried(self):
        # Response for role name that have a non 200 status code should
        # be retried.
        self.add_imds_response(body=b'')
        self.add_get_region_imds_response()
        result = InstanceMetadataRegionFetcher(
            num_attempts=2).retrieve_region()
        expected_result = 'us-mars-1'
        self.assertEqual(result, expected_result)

    def test_non_200_response_is_retried(self):
        # Response for creds that has a 200 status code but has an empty
        # body should be retried.
        self.add_imds_token_response()
        self.add_imds_response(
            status_code=429, body=b'{"message": "Slow down"}')
        self.add_get_region_imds_response()
        result = InstanceMetadataRegionFetcher(
            num_attempts=2).retrieve_region()
        expected_result = 'us-mars-1'
        self.assertEqual(result, expected_result)

    def test_http_connection_errors_is_retried(self):
        # Connection related errors should be retried
        self.add_imds_token_response()
        self.add_imds_connection_error(ConnectionClosedError(endpoint_url=''))
        self.add_get_region_imds_response()
        result = InstanceMetadataRegionFetcher(
            num_attempts=2).retrieve_region()
        expected_result = 'us-mars-1'
        self.assertEqual(result, expected_result)

    def test_empty_response_is_retried(self):
        # Response for creds that has a 200 status code but is empty.
        # This should be retried.
        self.add_imds_response(body=b'')
        self.add_get_region_imds_response()
        result = InstanceMetadataRegionFetcher(
            num_attempts=2).retrieve_region()
        expected_result = 'us-mars-1'
        self.assertEqual(result, expected_result)

    def test_exhaust_retries_on_region_request(self):
        self.add_imds_token_response()
        self.add_imds_response(status_code=400, body=b'')
        result = InstanceMetadataRegionFetcher(
            num_attempts=1).retrieve_region()
        self.assertEqual(result, None)


class TestIMDSRegionProvider(BaseIMDSRegionTest):
    def assert_does_provide_expected_value(self, fetcher_region=None,
                                           expected_result=None,):
        fake_session = mock.Mock(spec=session.Session)
        fake_fetcher = mock.Mock(spec=InstanceMetadataRegionFetcher)
        fake_fetcher.retrieve_region.return_value = fetcher_region
        provider = IMDSRegionProvider(fake_session, fetcher=fake_fetcher)
        value = provider.provide()
        self.assertEqual(value, expected_result)

    def test_does_provide_region_when_present(self):
        self.assert_does_provide_expected_value(
            fetcher_region='us-mars-2',
            expected_result='us-mars-2',
        )

    def test_does_provide_none(self):
        self.assert_does_provide_expected_value(
            fetcher_region=None,
            expected_result=None,
        )

    def test_use_truncated_user_agent(self):
        driver = create_clidriver()
        driver.session.user_agent_version = '3.0'
        self.add_imds_token_response()
        self.add_get_region_imds_response()
        provider = IMDSRegionProvider(driver.session)
        provider.provide()
        args, _ = self._send.call_args
        self.assertEqual(args[0].headers['User-Agent'], 'aws-cli/3.0')

    def test_can_use_ipv6(self):
        driver = create_clidriver()
        driver.session.set_config_variable('imds_use_ipv6', True)
        self.add_imds_token_response()
        self.add_get_region_imds_response()
        provider = IMDSRegionProvider(driver.session)
        provider.provide()
        args, _ = self._send.call_args
        self.assertIn('[fd00:ec2::254]', args[0].url)

    def test_use_ipv4_by_default(self):
        driver = create_clidriver()
        self.add_imds_token_response()
        self.add_get_region_imds_response()
        provider = IMDSRegionProvider(driver.session)
        provider.provide()
        args, _ = self._send.call_args
        self.assertIn('169.254.169.254', args[0].url)

    def test_can_set_imds_endpoint_mode_to_ipv4(self):
        driver = create_clidriver()
        driver.session.set_config_variable(
            'ec2_metadata_service_endpoint_mode', 'ipv4')
        self.add_imds_token_response()
        self.add_get_region_imds_response()
        provider = IMDSRegionProvider(driver.session)
        provider.provide()
        args, _ = self._send.call_args
        self.assertIn('169.254.169.254', args[0].url)

    def test_can_set_imds_endpoint_mode_to_ipv6(self):
        driver = create_clidriver()
        driver.session.set_config_variable(
            'ec2_metadata_service_endpoint_mode', 'ipv6')
        self.add_imds_token_response()
        self.add_get_region_imds_response()
        provider = IMDSRegionProvider(driver.session)
        provider.provide()
        args, _ = self._send.call_args
        self.assertIn('[fd00:ec2::254]', args[0].url)

    def test_can_set_imds_service_endpoint(self):
        driver = create_clidriver()
        driver.session.set_config_variable(
            'ec2_metadata_service_endpoint', 'http://myendpoint/')
        self.add_imds_token_response()
        self.add_get_region_imds_response()
        provider = IMDSRegionProvider(driver.session)
        provider.provide()
        args, _ = self._send.call_args
        self.assertIn('http://myendpoint/', args[0].url)
    
    def test_can_set_imds_service_endpoint_custom(self):
        driver = create_clidriver()
        driver.session.set_config_variable(
            'ec2_metadata_service_endpoint', 'http://myendpoint')
        self.add_imds_token_response()
        self.add_get_region_imds_response()
        provider = IMDSRegionProvider(driver.session)
        provider.provide()
        args, _ = self._send.call_args
        self.assertIn('http://myendpoint/', args[0].url)

    def test_imds_service_endpoint_overrides_ipv6_endpoint(self):
        driver = create_clidriver()
        driver.session.set_config_variable(
            'ec2_metadata_service_endpoint_mode', 'ipv6')
        driver.session.set_config_variable(
            'ec2_metadata_service_endpoint', 'http://myendpoint/')
        self.add_imds_token_response()
        self.add_get_region_imds_response()
        provider = IMDSRegionProvider(driver.session)
        provider.provide()
        args, _ = self._send.call_args
        self.assertIn('http://myendpoint/', args[0].url)

    def test_disable_ec2_metadata_v1(self):
        driver = create_clidriver()
        driver.session.set_config_variable('ec2_metadata_v1_disabled', True)
        self.add_imds_response(b'', 404)
        provider = IMDSRegionProvider(driver.session)
        with self.assertRaises(MetadataRetrievalError):
            provider.provide()


class TestLazyPager(unittest.TestCase):
    def setUp(self):
        self.popen = mock.Mock(subprocess.Popen)
        self.pager = LazyPager(self.popen)

    def test_lazy_pager_process_not_created_on_communicate_call_wo_args(self):
        stdout, stderr = self.pager.communicate()
        self.assertEqual(self.popen.call_count, 0)
        self.assertIsNone(stdout)
        self.assertIsNone(stderr)

    def test_lazy_pager_process_not_created_on_stdin_flush(self):
        self.pager.stdin.flush()
        self.assertEqual(self.popen.call_count, 0)

    def test_lazy_pager_popen_communicate_calls_on_call_with_args(self):
        process = mock.Mock(subprocess.Popen)
        self.popen.return_value = process
        pager = LazyPager(self.popen)
        pager.communicate(timeout=20)
        self.assertEqual(self.popen.call_count, 1)
        process.communicate.assert_called_with(timeout=20)

    def test_lazy_pager_popen_calls_on_stdin_call(self):
        self.pager.stdin.foo()
        self.assertEqual(self.popen.call_count, 1)

    def test_lazy_pager_popen_calls_on_process_call(self):
        self.pager.foo()
        self.assertEqual(self.popen.call_count, 1)


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


class TestDumpYamlToStr(unittest.TestCase):
    def setUp(self):
        self.yaml = ruamel.yaml.YAML(typ="safe", pure=True)
        self.yaml.representer.default_flow_style = False

    def test_dump_to_str(self):
        obj = {'A': 1, 'parameter': "something"}
        expected_result = "A: 1\nparameter: something\n"
        result = dump_yaml_to_str(self.yaml, obj)
        self.assertEqual(result, expected_result)


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


@pytest.fixture
def test_session():
    test_session = mock.Mock(session.Session)
    test_session.user_agent_extra = ''
    return test_session


def test_add_metadata_component_to_user_agent_extra(test_session):
    add_metadata_component_to_user_agent_extra(test_session, 'name', 'value')
    assert test_session.user_agent_extra == 'md/name#value'


def test_add_command_lineage_to_user_agent_extra(test_session):
    add_command_lineage_to_user_agent_extra(test_session, ['a', 'b', 'c'])
    assert test_session.user_agent_extra == 'md/command#a.b.c'


def test_no_add_command_lineage_to_user_agent_extra_with_existing_command_lineage(test_session):
    test_session.user_agent_extra = 'md/command#a.b.c'
    add_command_lineage_to_user_agent_extra(test_session, ['a', 'b', 'c', 'd'])
    assert test_session.user_agent_extra == 'md/command#a.b.c'
