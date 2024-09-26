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
import tempfile
import collections

from awscli.testutils import mock, unittest
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
                                    disable_rollback=True,
                                    capabilities=None,
                                    role_arn=None,
                                    notification_arns=[],
                                    fail_on_empty_changeset=True,
                                    s3_bucket=None,
                                    s3_prefix="some prefix",
                                    kms_key_id="some kms key id",
                                    force_upload=True,
                                    tags=["tagkey1=tagvalue1"])
        self.parsed_globals = FakeArgs(region="us-east-1", endpoint_url=None,
                                       verify_ssl=None)
        self.deploy_command = DeployCommand(self.session)

        self.deployer = Deployer(mock.Mock())
        self.deployer.create_and_wait_for_changeset = mock.Mock()
        self.deployer.execute_changeset = mock.Mock()
        self.deployer.wait_for_execute = mock.Mock()

    @mock.patch("awscli.customizations.cloudformation.deploy.yaml_parse")
    def test_command_invoked(self, mock_yaml_parse):
        """
        Tests that deploy method is invoked when command is run
        """
        fake_parameter_overrides = []
        fake_tags_dict = {"tagkey1": "tagvalue1"}
        fake_tags = [{"Key": "tagkey1", "Value": "tagvalue1"}]
        fake_parameters = "some return value"
        template_str = "some template"

        with tempfile.NamedTemporaryFile() as handle:
            file_path = handle.name

            open_mock = mock.mock_open()
            # Patch the file open method to return template string
            with mock.patch(
                    "awscli.customizations.cloudformation.deploy.open",
                    open_mock(read_data=template_str)) as open_mock:

                fake_template = get_example_template()
                mock_yaml_parse.return_value = fake_template

                self.deploy_command.deploy = mock.MagicMock()
                self.deploy_command.deploy.return_value = 0
                self.deploy_command.parse_key_value_arg = mock.Mock()
                self.deploy_command.parse_key_value_arg.side_effect = [
                    fake_parameter_overrides, fake_tags_dict]
                self.deploy_command.merge_parameters = mock.MagicMock(
                        return_value=fake_parameters)

                self.parsed_args.template_file = file_path
                result = self.deploy_command._run_main(self.parsed_args,
                                              parsed_globals=self.parsed_globals)
                self.assertEqual(0, result)

                open_mock.assert_called_once_with(file_path, "r")

                self.deploy_command.deploy.assert_called_once_with(
                    mock.ANY,
                    'some_stack_name',
                    mock.ANY,
                    fake_parameters,
                    None,
                    not self.parsed_args.no_execute_changeset,
                    None,
                    [],
                    None,
                    fake_tags,
                    True,
                    True
                )

                self.deploy_command.parse_key_value_arg.assert_has_calls([
                    mock.call(
                        self.parsed_args.parameter_overrides,
                         "parameter-overrides"
                    ),
                    mock.call(
                        self.parsed_args.tags,
                        "tags"
                    )
                ])

                self.deploy_command.merge_parameters.assert_called_once_with(
                        fake_template, fake_parameter_overrides)

                self.assertEqual(1, mock_yaml_parse.call_count)

    def test_invalid_template_file(self):
        self.parsed_args.template_file = "sometemplate"
        with self.assertRaises(exceptions.InvalidTemplatePathError):
            result = self.deploy_command._run_main(self.parsed_args,
                                                  parsed_globals=self.parsed_globals)

    @mock.patch('awscli.customizations.cloudformation.deploy.os.path.isfile')
    @mock.patch('awscli.customizations.cloudformation.deploy.yaml_parse')
    @mock.patch('awscli.customizations.cloudformation.deploy.os.path.getsize')
    def test_s3_upload_required_but_missing_bucket(self, mock_getsize, mock_yaml_parse, mock_isfile):
        """
        Tests that large templates are detected prior to deployment
        """
        template_str = get_example_template()

        mock_getsize.return_value = 51201
        mock_isfile.return_value = True
        mock_yaml_parse.return_value = template_str
        open_mock = mock.mock_open()

        with mock.patch(
                "awscli.customizations.cloudformation.deploy.open",
                open_mock(read_data=template_str)) as open_mock:
            with self.assertRaises(exceptions.DeployBucketRequiredError):
                result = self.deploy_command._run_main(self.parsed_args,
                                parsed_globals=self.parsed_globals)

    @mock.patch('awscli.customizations.cloudformation.deploy.os.path.isfile')
    @mock.patch('awscli.customizations.cloudformation.deploy.yaml_parse')
    @mock.patch('awscli.customizations.cloudformation.deploy.os.path.getsize')
    @mock.patch('awscli.customizations.cloudformation.deploy.DeployCommand.deploy')
    @mock.patch('awscli.customizations.cloudformation.deploy.S3Uploader')
    def test_s3_uploader_is_configured_properly(self, s3UploaderMock,
        deploy_method_mock, mock_getsize, mock_yaml_parse, mock_isfile):
        """
        Tests that large templates are detected prior to deployment
        """
        bucket_name = "mybucket"
        template_str = get_example_template()

        mock_getsize.return_value = 1024
        mock_isfile.return_value = True
        mock_yaml_parse.return_value = template_str
        open_mock = mock.mock_open()

        with mock.patch(
                "awscli.customizations.cloudformation.deploy.open",
                open_mock(read_data=template_str)) as open_mock:

            self.parsed_args.s3_bucket = bucket_name
            s3UploaderObject = mock.Mock()
            s3UploaderMock.return_value = s3UploaderObject

            result = self.deploy_command._run_main(self.parsed_args,
                            parsed_globals=self.parsed_globals)

            self.deploy_command.deploy.assert_called_once_with(
                mock.ANY,
                self.parsed_args.stack_name,
                mock.ANY,
                mock.ANY,
                None,
                not self.parsed_args.no_execute_changeset,
                None,
                [],
                s3UploaderObject,
                [{"Key": "tagkey1", "Value": "tagvalue1"}],
                True,
                True
            )

            s3UploaderMock.assert_called_once_with(mock.ANY,
                    bucket_name,
                    self.parsed_args.s3_prefix,
                    self.parsed_args.kms_key_id,
                    self.parsed_args.force_upload)

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
        role_arn = "arn:aws:iam::1234567890:role"
        notification_arns = ["arn:aws:sns:region:1234567890:notify"]
        s3_uploader = None
        tags = [{"Key":"key1", "Value": "val1"}]

        # Set the mock to return this fake changeset_id
        self.deployer.create_and_wait_for_changeset.return_value = ChangeSetResult(changeset_id, changeset_type)

        rc = self.deploy_command.deploy(self.deployer,
                                   stack_name,
                                   template,
                                   parameters,
                                   capabilities,
                                   execute_changeset,
                                   role_arn,
                                   notification_arns,
                                   s3_uploader,
                                   tags)
        self.assertEqual(rc, 0)


        self.deployer.create_and_wait_for_changeset.assert_called_once_with(stack_name=stack_name,
                                                     cfn_template=template,
                                                     parameter_values=parameters,
                                                     capabilities=capabilities,
                                                     role_arn=role_arn,
                                                     notification_arns=notification_arns,
                                                     s3_uploader=s3_uploader,
                                                     tags=tags)

        # since execute_changeset is set to True, deploy() will execute changeset
        self.deployer.execute_changeset.assert_called_once_with(changeset_id, stack_name, False)
        self.deployer.wait_for_execute.assert_called_once_with(stack_name, changeset_type)


    def test_deploy_no_execute(self):
        stack_name = "stack_name"
        changeset_id = "some changeset"
        parameters = ["a", "b"]
        template = "cloudformation template"
        capabilities = ["foo", "bar"]
        execute_changeset = False
        role_arn = "arn:aws:iam::1234567890:role"
        notification_arns = ["arn:aws:sns:region:1234567890:notify"]
        s3_uploader = None
        tags = [{"Key":"key1", "Value": "val1"}]


        self.deployer.create_and_wait_for_changeset.return_value = ChangeSetResult(changeset_id, "CREATE")
        rc = self.deploy_command.deploy(self.deployer,
                                            stack_name,
                                            template,
                                            parameters,
                                            capabilities,
                                            execute_changeset,
                                            role_arn,
                                            notification_arns,
                                            s3_uploader,
                                            tags)
        self.assertEqual(rc, 0)

        self.deployer.create_and_wait_for_changeset.assert_called_once_with(stack_name=stack_name,
                                                     cfn_template=template,
                                                     parameter_values=parameters,
                                                     capabilities=capabilities,
                                                     role_arn=role_arn,
                                                     notification_arns=notification_arns,
                                                     s3_uploader=s3_uploader,
                                                     tags=tags)

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
        role_arn = "arn:aws:iam::1234567890:role"
        notification_arns = ["arn:aws:sns:region:1234567890:notify"]
        s3_uploader = None
        tags = [{"Key":"key1", "Value": "val1"}]

        self.deployer.wait_for_execute.side_effect = RuntimeError("Some error")
        with self.assertRaises(RuntimeError):
            self.deploy_command.deploy(self.deployer,
                                       stack_name,
                                       template,
                                       parameters,
                                       capabilities,
                                       execute_changeset,
                                       role_arn,
                                       notification_arns,
                                       s3_uploader,
                                       tags)

    def test_deploy_raises_exception_on_empty_changeset(self):
        stack_name = "stack_name"
        parameters = ["a", "b"]
        template = "cloudformation template"
        capabilities = ["foo", "bar"]
        execute_changeset = True
        role_arn = "arn:aws:iam::1234567890:role"
        notification_arns = ["arn:aws:sns:region:1234567890:notify"]
        tags = []

        empty_changeset = exceptions.ChangeEmptyError(stack_name=stack_name)
        changeset_func = self.deployer.create_and_wait_for_changeset
        changeset_func.side_effect = empty_changeset
        with self.assertRaises(exceptions.ChangeEmptyError):
            self.deploy_command.deploy(
                self.deployer, stack_name, template, parameters, capabilities,
                execute_changeset, role_arn, notification_arns,
                None, tags)

    def test_deploy_does_not_raise_exception_on_empty_changeset(self):
        stack_name = "stack_name"
        parameters = ["a", "b"]
        template = "cloudformation template"
        capabilities = ["foo", "bar"]
        execute_changeset = True
        role_arn = "arn:aws:iam::1234567890:role"
        notification_arns = ["arn:aws:sns:region:1234567890:notify"]

        empty_changeset = exceptions.ChangeEmptyError(stack_name=stack_name)
        changeset_func = self.deployer.create_and_wait_for_changeset
        changeset_func.side_effect = empty_changeset
        self.deploy_command.deploy(
            self.deployer, stack_name, template, parameters, capabilities,
            execute_changeset, role_arn, notification_arns,
            s3_uploader=None, tags=[],
            fail_on_empty_changeset=False
        )

    def test_parse_key_value_arg_success(self):
        """
        Tests that we can parse parameter arguments provided in proper format
        Expected format: ["Key=Value", "Key=Value"]
        :return:
        """
        argname = "parameter-overrides"
        data = ["Key1=Value1", 'Key2=[1,2,3]', 'Key3={"a":"val", "b": 2}']
        output = {"Key1": "Value1", "Key2": '[1,2,3]', "Key3": '{"a":"val", "b": 2}'}

        result = self.deploy_command.parse_key_value_arg(data, argname)
        self.assertEqual(result, output)

        # Empty input should return empty output
        result = self.deploy_command.parse_key_value_arg([], argname)
        self.assertEqual(result, {})

    def test_parse_key_value_arg_invalid_input(self):
        # non-list input
        argname = "parameter-overrides"
        with self.assertRaises(exceptions.InvalidKeyValuePairArgumentError):
            self.deploy_command.parse_key_value_arg("hello=world", argname)

        # missing equal to sign
        with self.assertRaises(exceptions.InvalidKeyValuePairArgumentError):
            self.deploy_command.parse_key_value_arg(["hello world"], argname)

    def test_merge_parameters_success(self):
        """
        Tests that we can merge parameters specified in CloudFormation template
        with override values specified as commandline arguments
        """
        template = {
            "Parameters": {
                "Key1": {"Type": "String"},
                "Key2": {"Type": "String"},
                "Key3": "Something",
                "Key4": {"Type": "Number"},
                "KeyWithDefaultValue": {"Type": "String", "Default": "something"},
                "KeyWithDefaultValueButOverridden": {"Type": "String", "Default": "something"}
            }
        }
        overrides = {
            "Key1": "Value1",
            "Key3": "Value3",
            "KeyWithDefaultValueButOverridden": "Value4"
        }

        expected_result = [
            # Overridden values
            {"ParameterKey": "Key1", "ParameterValue": "Value1"},
            {"ParameterKey": "Key3", "ParameterValue": "Value3"},

            # Parameter contains default value, but overridden with new value
            {"ParameterKey": "KeyWithDefaultValueButOverridden", "ParameterValue": "Value4"},

            # non-overridden values
            {"ParameterKey": "Key2", "UsePreviousValue": True},
            {"ParameterKey": "Key4", "UsePreviousValue": True},

            # Parameter with default value but NOT overridden.
            # Use previous value, but this gets removed later when we are creating stack for first time
            {"ParameterKey": "KeyWithDefaultValue", "UsePreviousValue": True},
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
