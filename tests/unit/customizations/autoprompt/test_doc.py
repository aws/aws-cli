# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import mock
import textwrap

from awscli.clidriver import create_clidriver
from awscli.customizations.autoprompt.doc import (
    AwsTopLevelDocsGetter, BaseDocsGetter, DocsGetter,
    ServiceCommandDocsGetter, ServiceOperationDocsGetter
)
from awscli.testutils import unittest


class TestDocsGetter(unittest.TestCase):
    def setUp(self):
        self.driver = create_clidriver()
        self.aws_top_level_docs_getter = mock.Mock(spec=AwsTopLevelDocsGetter)
        self.aws_top_level_docs_getter.get_docs = mock.Mock()
        self.service_command_docs_getter = \
            mock.Mock(spec=ServiceCommandDocsGetter)
        self.service_command_docs_getter.get_docs = mock.Mock()
        self.docs_getter = DocsGetter(
            driver=self.driver,
            aws_top_level_docs_getter=self.aws_top_level_docs_getter,
            service_command_docs_getter=self.service_command_docs_getter)

    def test_delegates_to_top_level_docs_getter_if_empty_command(self):
        command_text = ''
        self.docs_getter.get_docs(command_text)
        self.assertTrue(
            self.docs_getter.aws_top_level_docs_getter.get_docs.called)

    def test_delegates_to_top_level_docs_getter_if_invalid_command(self):
        command_text = 'fake'
        self.docs_getter.get_docs(command_text)
        self.assertTrue(
            self.docs_getter.aws_top_level_docs_getter.get_docs.called)

    def test_delegates_to_service_command_docs_getter_if_valid_command(self):
        command_text = 'ec2'
        self.docs_getter.get_docs(command_text)
        self.assertTrue(
            self.docs_getter.service_command_docs_getter.get_docs.called)

    def test_delegates_to_service_command_docs_getter_if_valid_operation(self):
        # We delegate to the service command docs getter here, which will then
        # delegate to the service operation docs getter internally.
        command_text = 'ec2 describe-instances'
        self.docs_getter.get_docs(command_text)
        self.assertTrue(
            self.docs_getter.service_command_docs_getter.get_docs.called)

    def test_delegates_to_service_operation_getter_if_option_specified(self):
        # We delegate to the service command docs getter here, which will then
        # delegate to the service operation docs getter internally.
        command_text = 'ec2 describe-instances --output'
        self.docs_getter.get_docs(command_text)
        self.assertTrue(
            self.docs_getter.service_command_docs_getter.get_docs.called)

    def test_delegates_to_top_level_docs_getter_if_aws_help_is_entered(self):
        command_text = 'help'
        self.docs_getter.get_docs(command_text)
        self.assertTrue(
            self.docs_getter.aws_top_level_docs_getter.get_docs.called)

    def test_delegates_to_service_operation_getter_if_file_path_is_specified(self):
        command_text = 's3 ls file://path/to/file.txt'
        self.docs_getter.get_docs(command_text)
        self.assertTrue(
            self.docs_getter.service_command_docs_getter.get_docs.called)


class TestBaseDocsGetter(unittest.TestCase):
    def setUp(self):
        self.driver = create_clidriver()
        self.help_command = self.driver.create_help_command()
        self.help_command.doc = mock.Mock()
        self.help_command.doc.getvalue = mock.Mock()
        self.base_docs_getter = BaseDocsGetter(self.driver)

    def test_get_doc_content(self):
        self.help_command.doc.getvalue.return_value = b'Dummy content.'
        content = self.base_docs_getter.get_doc_content(self.help_command)
        self.assertEqual(content, 'Dummy content.\n')

    def test_get_rst_doc_in_txt(self):
        content = textwrap.dedent("""\
            MySection
            =========

            This is some text.
            Here's a list:

            * foo
            * bar

            Literal text: ``--foo-bar``
        """)
        expected_response = textwrap.dedent("""\

            MYSECTION

            This is some text. Here's a list:

            * foo

            * bar

            Literal text: --foo-bar
        """)
        self.help_command.doc.getvalue.return_value = content.encode('utf-8')
        response = self.base_docs_getter.get_doc_content(self.help_command)
        self.assertEqual(response, expected_response)

    def test_get_empty_doc_content(self):
        self.help_command.doc.getvalue.return_value = b''
        content = self.base_docs_getter.get_doc_content(self.help_command)
        self.assertEqual(content, '')


class TestAwsTopLevelDocsGetter(unittest.TestCase):
    def setUp(self):
        self.driver = create_clidriver()
        self.aws_top_level_docs_getter = AwsTopLevelDocsGetter(self.driver)
        self.aws_top_level_docs_getter.get_doc_content = mock.Mock()

    def test_base_docs_getter_is_called(self):
        self.aws_top_level_docs_getter.get_docs(self.driver)
        self.assertTrue(self.aws_top_level_docs_getter.get_doc_content.called)

    def test_base_docs_getter_use_cache(self):
        self.aws_top_level_docs_getter.get_docs(self.driver)
        self.assertEqual(
            self.aws_top_level_docs_getter.get_doc_content.call_count, 1
        )
        self.aws_top_level_docs_getter.get_docs(self.driver)
        self.assertEqual(
            self.aws_top_level_docs_getter.get_doc_content.call_count, 1
        )


class TestServiceCommandDocsGetter(unittest.TestCase):
    def setUp(self):
        self.driver = create_clidriver()
        self.service_operation_docs_getter = \
            mock.Mock(spec=ServiceOperationDocsGetter)
        self.service_operation_docs_getter.get_docs = mock.Mock()
        self.service_command_docs_getter = ServiceCommandDocsGetter(
            self.driver, self.service_operation_docs_getter)
        self.service_command_docs_getter.get_doc_content = mock.Mock()

    def test_calls_base_docs_getter_if_no_remaining_args(self):
        args = ['ec2']
        self.service_command_docs_getter.get_docs(args)
        self.assertTrue(self.service_command_docs_getter.get_doc_content.called)

    def test_calls_base_docs_getter_if_service_operation_is_invalid(self):
        args = ['ec2', 'fake']
        self.service_command_docs_getter.get_docs(args)
        self.assertTrue(self.service_command_docs_getter.get_doc_content.called)

    def test_calls_service_operation_docs_getter_if_remaining_args_exist(self):
        args = ['ec2', 'describe-instances']
        self.service_command_docs_getter.get_docs(args)
        self.assertTrue(self.service_operation_docs_getter.get_docs.called)   

    def test_base_docs_getter_use_cache(self):
        args = ['ec2']
        self.service_command_docs_getter.get_docs(args)
        self.assertEqual(
            self.service_command_docs_getter.get_doc_content.call_count, 1
        )
        self.service_command_docs_getter.get_docs(args)
        self.assertEqual(
            self.service_command_docs_getter.get_doc_content.call_count, 1
        )


class TestServiceOperationDocsGetter(unittest.TestCase):
    def setUp(self):
        self.driver = create_clidriver()
        self.service_command_table = self.driver.subcommand_table
        self.service_operation_docs_getter = \
            ServiceOperationDocsGetter(self.driver)
        self.service_operation_docs_getter.get_doc_content = mock.Mock()

    def get_service_command(self, args):
        parser = self.driver.create_parser(self.service_command_table)
        parsed_args, remaining = parser.parse_known_args(args)
        service_name = parsed_args.command
        return self.service_command_table[service_name], remaining

    def test_calls_base_docs_getter_if_valid_service_operation(self):
        args = ['ec2', 'describe-instances']
        self.service_command, remaining = self.get_service_command(args)
        self.service_operation_docs_getter.get_docs(
            self.service_command, remaining)
        self.assertTrue(
            self.service_operation_docs_getter.get_doc_content.called)

    def test_calls_base_docs_getter_with_custom_service_commands_and_operations(self):
        args = ['s3', 'ls']
        self.service_command, remaining = self.get_service_command(args)
        self.service_operation_docs_getter.get_docs(
            self.service_command, remaining)
        self.assertTrue(
            self.service_operation_docs_getter.get_doc_content.called)

    def test_base_docs_getter_use_cache(self):
        args = ['ec2', 'describe-instances']
        self.service_command, remaining = self.get_service_command(args)
        self.service_operation_docs_getter.get_docs(
            self.service_command, remaining)
        self.assertEqual(
            self.service_operation_docs_getter.get_doc_content.call_count, 1)
        self.service_operation_docs_getter.get_docs(
            self.service_command, remaining)
        self.assertEqual(
            self.service_operation_docs_getter.get_doc_content.call_count, 1)
