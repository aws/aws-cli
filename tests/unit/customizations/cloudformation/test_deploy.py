# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0e
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import mock
import tempfile
import six
from mock import patch, Mock, MagicMock
import collections

from awscli.testutils import unittest
from awscli.customizations.cloudformation.deploy import DeployCommand
from awscli.customizations.cloudformation.deployer import Deployer
from awscli.customizations.cloudformation.yamlhelper import yaml_parse
from awscli.customizations.cloudformation import exceptions


class FakeArgs(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __contains__(self, key):
        return key in self.__dict__


def get_example_template():
    return {
        "Parameters": {
            "Key1": "Value1"
        },
        "Resources": {
            "Resource1": {}
        }
    }

ChangeSetResult = collections.namedtuple("ChangeSetResult", ["changeset_id", "changeset_type"])

class TestDeployCommand(unittest.TestCase):

    def setUp(self):
        self.session = mock.Mock()
        self.session.get_scoped_config.return_value = {}
        self.parsed_args = FakeArgs(template_file='./foo',
                                    stack_name="some_stack_name",
                                    parameter_overrides=["Key1=Value1",
                                                         "Key2=Value2"],
                                    no_execute_changeset=False,
                                    execute_changeset=True,
                                    capabilities=None)
        self.parsed_globals = FakeArgs(region="us-east-1", endpoint_url=None,
                                       verify_ssl=None)
        self.deploy_command = DeployCommand(self.session)

        self.deployer = Deployer(Mock())
        self.deployer.create_and_wait_for_changeset = Mock()
        self.deployer.execute_changeset = Mock()
        self.deployer.wait_for_execute = Mock()

    @patch("awscli.customizations.cloudformation.deploy.yaml_parse")
    def test_command_invoked(self, mock_yaml_parse):
        """
        Tests that deploy method is invoked when command is run
        """
        fake_parameter_overrides = []
        fake_parameters = "some return value"
        template_str = "some template"

        with tempfile.NamedTemporaryFile() as handle:
            file_path = handle.name

            open_mock = mock.mock_open()
            # Patch the file open method to return template string
            with patch(
                    "awscli.customizations.cloudformation.deploy.open",
                    open_mock(read_data=template_str)) as open_mock:

                fake_template = get_example_template()
                mock_yaml_parse.return_value = fake_template

                self.deploy_command.deploy = MagicMock()
                self.deploy_command.deploy.return_value = 0
                self.deploy_command.parse_parameter_arg = MagicMock(
                        return_value=fake_parameter_overrides)
                self.deploy_command.merge_parameters = MagicMock(
                        return_value=fake_parameters)

                self.parsed_args.template_file = file_path
                result = self.deploy_command._run_main(self.parsed_args,
                                              parsed_globals=self.parsed_globals)
                self.assertEquals(0, result)

                open_mock.assert_called_once_with(file_path, "r")

                self.deploy_command.deploy.assert_called_once_with(
                        mock.ANY,
                        self.parsed_args.stack_name,
                        mock.ANY,
                        fake_parameters,
                        None,
                        not self.parsed_args.no_execute_changeset)

                self.deploy_command.parse_parameter_arg.assert_called_once_with(
                        self.parsed_args.parameter_overrides)

                self.deploy_command.merge_parameters.assert_called_once_with(
                        fake_template, fake_parameter_overrides)

                self.assertEquals(1, mock_yaml_parse.call_count)

    def test_invalid_template_file(self):
        self.parsed_args.template_file = "sometemplate"
        with self.assertRaises(exceptions.InvalidTemplatePathError):
            result = self.deploy_command._run_main(self.parsed_args,
                                                  parsed_globals=self.parsed_globals)


    def test_deploy_success(self):
        """
        Tests that we call the deploy command
        """

        stack_name = "stack_name"
        changeset_id = "some changeset"
        parameters = ["a", "b"]
        template = "cloudformation template"
        capabilities = ["foo", "bar"]
        execute_changeset = True
        changeset_type = "CREATE"

        # Set the mock to return this fake changeset_id
        self.deployer.create_and_wait_for_changeset.return_value = ChangeSetResult(changeset_id, changeset_type)

        rc = self.deploy_command.deploy(self.deployer,
                                   stack_name,
                                   template,
                                   parameters,
                                   capabilities,
                                   execute_changeset)
        self.assertEqual(rc, 0)


        self.deployer.create_and_wait_for_changeset.assert_called_once_with(stack_name=stack_name,
                                                     cfn_template=template,
                                                     parameter_values=parameters,
                                                     capabilities=capabilities)

        # since execute_changeset is set to True, deploy() will execute changeset
        self.deployer.execute_changeset.assert_called_once_with(changeset_id, stack_name)
        self.deployer.wait_for_execute.assert_called_once_with(stack_name, changeset_type)


    def test_deploy_no_execute(self):
        stack_name = "stack_name"
        changeset_id = "some changeset"
        parameters = ["a", "b"]
        template = "cloudformation template"
        capabilities = ["foo", "bar"]
        execute_changeset = False


        self.deployer.create_and_wait_for_changeset.return_value = ChangeSetResult(changeset_id, "CREATE")
        rc = self.deploy_command.deploy(self.deployer,
                                            stack_name,
                                            template,
                                            parameters,
                                            capabilities,
                                            execute_changeset)
        self.assertEqual(rc, 0)

        self.deployer.create_and_wait_for_changeset.assert_called_once_with(stack_name=stack_name,
                                                     cfn_template=template,
                                                     parameter_values=parameters,
                                                     capabilities=capabilities)

        # since execute_changeset is set to True, deploy() will execute changeset
        self.deployer.execute_changeset.assert_not_called()
        self.deployer.wait_for_execute.assert_not_called()

    def test_deploy_raise_exception(self):
        stack_name = "stack_name"
        changeset_id = "some changeset"
        parameters = ["a", "b"]
        template = "cloudformation template"
        capabilities = ["foo", "bar"]
        execute_changeset = True

        self.deployer.wait_for_execute.side_effect = RuntimeError("Some error")
        with self.assertRaises(RuntimeError):
            self.deploy_command.deploy(self.deployer,
                                       stack_name,
                                       template,
                                       parameters,
                                       capabilities,
                                       execute_changeset)


    def test_parse_parameter_arg_success(self):
        """
        Tests that we can parse parameter arguments provided in proper format
        Expected format: ["Key=Value", "Key=Value"]
        :return:
        """
        data = ["Key1=Value1", 'Key2=[1,2,3]', 'Key3={"a":"val", "b": 2}']
        output = {"Key1": "Value1", "Key2": '[1,2,3]', "Key3": '{"a":"val", "b": 2}'}

        result = self.deploy_command.parse_parameter_arg(data)
        self.assertEqual(result, output)

        # Empty input should return empty output
        result = self.deploy_command.parse_parameter_arg([])
        self.assertEqual(result, {})

    def test_parse_parameter_arg_invalid_input(self):
        # non-list input
        with self.assertRaises(exceptions.InvalidParameterOverrideArgumentError):
            self.deploy_command.parse_parameter_arg("hello=world")

        # missing equal to sign
        with self.assertRaises(exceptions.InvalidParameterOverrideArgumentError):
            self.deploy_command.parse_parameter_arg(["hello world"])

    def test_merge_parameters_success(self):
        """
        Tests that we can merge parameters specified in CloudFormation template
        with override values specified as commandline arguments
        """
        template = {
            "Parameters": {
                "Key1": {"Type": "String"}, "Key2": {"Type": "String"},
                "Key3": "Something", "Key4": {"Type": "Number"},
            }
        }
        overrides = {
            "Key1": "Value1",
            "Key3": "Value3"
        }

        expected_result = [
            # Overriden values
            {"ParameterKey": "Key1", "ParameterValue": "Value1"},
            {"ParameterKey": "Key3", "ParameterValue": "Value3"},

            # non-overriden values
            {"ParameterKey": "Key2", "UsePreviousValue": True},
            {"ParameterKey": "Key4", "UsePreviousValue": True},
        ]

        self.assertItemsEqual(
            self.deploy_command.merge_parameters(template, overrides),
            expected_result
        )

    def test_merge_parameters_success_nothing_to_override(self):
        """
        Tests that we can merge parameters specified in CloudFormation template
        with override values specified as commandline arguments
        """
        template = {
            "Parameters": {
                "Key1": {"Type": "String"}, "Key2": {"Type": "String"},
                "Key3": "Something", "Key4": {"Type": "Number"},
            }
        }
        overrides = {
            # Key5 is not in the template. We will simply skip this key
            "Key5": "Value5"
        }

        expected_result = [
            {"ParameterKey": "Key1", "UsePreviousValue": True},
            {"ParameterKey": "Key2", "UsePreviousValue": True},
            {"ParameterKey": "Key3", "UsePreviousValue": True},
            {"ParameterKey": "Key4", "UsePreviousValue": True},
        ]

        self.assertItemsEqual(
            self.deploy_command.merge_parameters(template, overrides),
            expected_result
        )

        # Parameters definition is empty. Nothing to override
        result = self.deploy_command.merge_parameters({"Parameters": {}},
                                                      overrides)
        self.assertEqual(result, [])

    def test_merge_parameters_invalid_input(self):

        # Template does not contain "Parameters" definition
        result = self.deploy_command.merge_parameters({}, {"Key": "Value"})
        self.assertEqual(result, [])

        # Parameters definition is invalid
        result = self.deploy_command.merge_parameters({"Parameters": "foo"},
                                                      {"Key": "Value"})
        self.assertEqual(result, [])
