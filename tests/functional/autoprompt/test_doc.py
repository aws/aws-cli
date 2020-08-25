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
from awscli.clidriver import create_clidriver, ServiceCommand
from awscli.customizations.autoprompt.doc import (
    AwsTopLevelDocsGetter, DocsGetter, ServiceCommandDocsGetter,
    ServiceOperationDocsGetter
)
from awscli.testutils import unittest


class TestDocsGetter(unittest.TestCase):
    def setUp(self):
        self.driver = create_clidriver()
        self.docs_getter = DocsGetter(self.driver)

    def test_get_service_command_docs(self):
        command_text = 'ec2'
        actual_docs = self.docs_getter.get_docs(command_text)
        expected_docs = 'Elastic Compute Cloud'
        self.assertIn(expected_docs, actual_docs)

    def test_get_service_operation_docs(self):
        command_text = 'ec2 describe-instances'
        actual_docs = self.docs_getter.get_docs(command_text)
        expected_docs = 'Describes the specified instances'
        self.assertIn(expected_docs, actual_docs)

    def test_get_top_level_aws_docs_if_no_command_specified(self):
        command_text = ''
        actual_docs = self.docs_getter.get_docs(command_text)
        expected_docs = 'The AWS Command Line Interface'
        self.assertIn(expected_docs, actual_docs)

    def test_get_top_level_aws_docs_if_service_command_is_invalid(self):
        command_text = 'fake'
        actual_docs = self.docs_getter.get_docs(command_text)
        expected_docs = 'The AWS Command Line Interface'
        self.assertIn(expected_docs, actual_docs)

    def test_get_service_command_docs_if_service_operation_is_invalid(self):
        # The service command docs will still be retrieved if the service
        # operation is invalid. The special case is if the invalid service
        # operation is entered at the entrypoint. In this case, the top-level
        # docs will be retrieved instead. However, this logic is handled
        # outside of the `DocsGetter` class.
        command_text = 'ec2 fake'
        actual_docs = self.docs_getter.get_docs(command_text)
        expected_docs = 'Elastic Compute Cloud'
        self.assertIn(expected_docs, actual_docs)


class TestAwsTopLevelDocsGetter(unittest.TestCase):
    """In this set of tests, we only compare the beginning of the help docs
    instead of checking against the entire top-level AWS help docs because the
    help docs are subject to change in the future. Any updates to the help docs
    would require these tests to get updated. Checking just the beginning of
    the help docs should minimize how often these tests need to get updated.

    """
    def setUp(self):
        self.driver = create_clidriver()
        self.docs_getter = AwsTopLevelDocsGetter(self.driver)
        self.help_docs = 'The AWS Command Line Interface'

    def test_can_get_top_level_aws_help_text(self):
        docs = self.docs_getter.get_docs(self.driver)
        self.assertIn(self.help_docs, docs)


class TestServiceCommandDocsGetter(unittest.TestCase):
    """In this set of tests, we only compare the beginning of the help docs
    instead of checking against the entire top-level AWS help docs because the
    help docs are subject to change in the future. Any updates to the help docs
    would require these tests to get updated. Checking just the beginning of
    the help docs should minimize how often these tests need to get updated.

    """
    def setUp(self):
        self.driver = create_clidriver()
        self.service_command_docs_getter = \
            ServiceCommandDocsGetter(self.driver)

    def test_can_get_service_command_docs_with_no_service_operation(self):
        args = ['ec2']
        actual_docs = self.service_command_docs_getter.get_docs(args)
        expected_docs = 'Elastic Compute Cloud'
        self.assertIn(expected_docs, actual_docs)

    def test_can_get_service_command_docs_with_valid_service_operation(self):
        args = ['ec2', 'describe-instances']
        actual_docs = self.service_command_docs_getter.get_docs(args)
        expected_docs = 'Describes the specified instances'
        self.assertIn(expected_docs, actual_docs)

    def test_can_get_service_command_docs_with_invalid_service_operation(self):
        args = ['ec2', 'fake']
        actual_docs = self.service_command_docs_getter.get_docs(args)
        expected_docs = 'Elastic Compute Cloud'
        self.assertIn(expected_docs, actual_docs)


class TestServiceOperationDocsGetter(unittest.TestCase):
    """In this set of tests, we only compare the beginning of the help docs
    instead of checking against the entire top-level AWS help docs because the
    help docs are subject to change in the future. Any updates to the help docs
    would require these tests to get updated. Checking just the beginning of
    the help docs should minimize how often these tests need to get updated.

    Note: We don't test against invalid service operation names here, as doing
    so would cause the parser to raise a SystemExit. The responsibility of
    handling invalid service operation names falls on the
    ServiceCommandDocsGetter, so we test for invalid service operation names
    there instead.

    """
    def setUp(self):
        self.driver = create_clidriver()
        self.service_operation_docs_getter = \
            ServiceOperationDocsGetter(self.driver)
        self.service_command = ServiceCommand(cli_name='ec2',
                                              session=self.driver.session,
                                              service_name='ec2')

    def test_can_get_service_operation_docs(self):
        remaining = ['describe-instances']
        actual_docs = self.service_operation_docs_getter.get_docs(
            self.service_command, remaining)
        expected_docs = 'Describes the specified instances'
        self.assertIn(expected_docs, actual_docs)
