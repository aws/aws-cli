# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import (
    mock,
    unittest,
    BaseAWSCommandParamsTest,
    create_clidriver,
    FileCreator,
)
from awscli.customizations.configure.configure import ConfigureCommand


class TestConfigureCommand(BaseAWSCommandParamsTest):
    def setUp(self):
        super().setUp()
        self.files = FileCreator()
        self.config_filename = self.files.full_path("configure")
        self.environ["AWS_CONFIG_FILE"] = self.config_filename
        self.environ["AWS_SHARED_CREDENTIALS_FILE"] = "asdf-does-not-exist"

    def tearDown(self):
        super().tearDown()
        self.files.remove_all()

    def set_config_file_contents(self, contents):
        self.files.create_file(self.config_filename, contents)
        # Reset the session to pick up the new config file.
        self.driver = create_clidriver()

    def get_config_file_contents(self):
        with open(self.config_filename, "r") as f:
            return f.read()

    def test_list_command(self):
        self.set_config_file_contents(
            "\n"
            "[default]\n"
            "aws_access_key_id=12345\n"
            "aws_secret_access_key=12345\n"
            "region=us-west-2\n"
        )
        self.environ.pop("AWS_DEFAULT_REGION", None)
        self.environ.pop("AWS_ACCESS_KEY_ID", None)
        self.environ.pop("AWS_SECRET_ACCESS_KEY", None)
        stdout, _, _ = self.run_cmd("configure list")
        self.assertRegex(stdout, r"access_key.+config-file")
        self.assertRegex(stdout, r"secret_key.+config-file")
        self.assertRegex(stdout, r"region\s+us-west-2\s+config-file")

    def test_get_command(self):
        self.driver = create_clidriver()
        self.set_config_file_contents(
            "\n"
            "[default]\n"
            "aws_access_key_id=access_key\n"
            "aws_secret_access_key=secret_key\n"
            "region=us-west-2\n"
        )
        stdout, _, _ = self.run_cmd("configure get aws_access_key_id")
        self.assertEqual(stdout.strip(), "access_key")

    def test_get_command_with_profile_set(self):
        self.set_config_file_contents(
            "\n"
            "[default]\n"
            "aws_access_key_id=default_access_key\n"
            "\n"
            "[profile testing]\n"
            "aws_access_key_id=testing_access_key\n"
        )
        stdout, _, _ = self.run_cmd(
            "configure get aws_access_key_id --profile testing",
        )
        self.assertEqual(stdout.strip(), "testing_access_key")

    def test_get_with_fq_name(self):
        # test get configs with fully qualified name.
        self.set_config_file_contents(
            "\n"
            "[default]\n"
            "aws_access_key_id=default_access_key\n"
            "\n"
            "[profile testing]\n"
            "aws_access_key_id=testing_access_key\n"
        )
        stdout, _, _ = self.run_cmd(
            "configure get default.aws_access_key_id --profile testing",
        )
        self.assertEqual(stdout.strip(), "default_access_key")

    def test_get_with_fq_profile_name(self):
        self.set_config_file_contents(
            "\n"
            "[default]\n"
            "aws_access_key_id=default_access_key\n"
            "\n"
            "[profile testing]\n"
            "aws_access_key_id=testing_access_key\n"
        )
        stdout, _, _ = self.run_cmd(
            "configure get profile.testing.aws_access_key_id "
            "--profile default",
        )
        self.assertEqual(stdout.strip(), "testing_access_key")

    def test_get_fq_with_quoted_profile_name(self):
        self.set_config_file_contents(
            "\n"
            "[default]\n"
            "aws_access_key_id=default_access_key\n"
            "\n"
            '[profile "testing"]\n'
            "aws_access_key_id=testing_access_key\n"
        )
        stdout, _, _ = self.run_cmd(
            "configure get profile.testing.aws_access_key_id "
            "--profile default",
        )
        self.assertEqual(stdout.strip(), "testing_access_key")

    def test_get_fq_for_non_profile_configs(self):
        self.set_config_file_contents(
            "\n"
            "[default]\n"
            "aws_access_key_id=default_access_key\n"
            "\n"
            "[profile testing]\n"
            "aws_access_key_id=testing_access_key\n"
            "[preview]\n"
            "emr=true"
        )
        stdout, _, _ = self.run_cmd(
            "configure get preview.emr --profile default",
        )
        self.assertEqual(stdout.strip(), "true")

    def test_set_with_config_file_no_exist(self):
        self.run_cmd("configure set region us-west-1")
        self.assertEqual(
            "[default]\n"
            "region = us-west-1\n",
            self.get_config_file_contents()
        )

    def test_set_with_a_url(self):
        self.run_cmd(
            "configure set endpoint http://www.example.com",
        )
        self.assertEqual(
            "[default]\n"
            "endpoint = http://www.example.com\n",
            self.get_config_file_contents(),
        )

    def test_set_with_empty_config_file(self):
        with open(self.config_filename, "w"):
            pass

        self.run_cmd("configure set region us-west-1")
        self.assertEqual(
            "[default]\n"
            "region = us-west-1\n",
            self.get_config_file_contents()
        )

    def test_set_with_updating_value(self):
        self.set_config_file_contents(
            "[default]\n"
            "region = us-west-2\n"
        )
        self.run_cmd("configure set region us-west-1")
        self.assertEqual(
            "[default]\n"
            "region = us-west-1\n",
            self.get_config_file_contents()
        )

    def test_set_with_profile_spaces(self):
        self.run_cmd(
            [
                "configure",
                "set",
                "region",
                "us-west-1",
                "--profile",
                "test with spaces",
            ]
        )
        self.assertEqual(
            "[profile 'test with spaces']\n"
            "region = us-west-1\n",
            self.get_config_file_contents(),
        )

    def test_set_with_profile_unknown_nested_key(self):
        self.run_cmd(
            [
                "configure",
                "set",
                "un.known",
                "us-west-1",
                "--profile",
                "space test",
            ]
        )
        self.assertEqual(
            "[profile 'space test']\n"
            "un =\n"
            "    known = us-west-1\n",
            self.get_config_file_contents(),
        )

    def test_set_with_profile_spaces_scoped(self):
        self.run_cmd(
            [
                "configure",
                "set",
                "profile.test with spaces.region",
                "us-west-1",
            ]
        )
        self.assertEqual(
            "[profile 'test with spaces']\n"
            "region = us-west-1\n",
            self.get_config_file_contents(),
        )

    def test_set_with_profile(self):
        self.run_cmd(
            "configure set region us-west-1 --profile testing",
        )
        self.assertEqual(
            "[profile testing]\n"
            "region = us-west-1\n",
            self.get_config_file_contents(),
        )

    def test_set_with_fq_single_dot(self):
        self.run_cmd("configure set preview.cloudsearch true")
        self.assertEqual(
            "[preview]\n"
            "cloudsearch = true\n",
            self.get_config_file_contents()
        )

    def test_set_with_fq_double_dot(self):
        self.run_cmd(
            "configure set profile.testing.region us-west-2",
        )
        self.assertEqual(
            "[profile testing]\n"
            "region = us-west-2\n",
            self.get_config_file_contents(),
        )

    def test_set_with_commented_out_field(self):
        self.set_config_file_contents(
            "#[preview]\n"
            ";cloudsearch = true\n"
        )
        self.run_cmd("configure set preview.cloudsearch true")
        self.assertEqual(
            "#[preview]\n"
            ";cloudsearch = true\n"
            "[preview]\n"
            "cloudsearch = true\n",
            self.get_config_file_contents(),
        )

    def test_set_with_triple_nesting(self):
        self.run_cmd(
            "configure set default.s3.signature_version s3v4",
        )
        self.assertEqual(
            "[default]\n"
            "s3 =\n"
            "    signature_version = s3v4\n",
            self.get_config_file_contents(),
        )

    def test_set_with_existing_config(self):
        self.set_config_file_contents(
            "[default]\n"
            "region = us-west-2\n"
            "ec2 =\n"
            "    signature_version = v4\n"
        )
        self.run_cmd(
            "configure set default.s3.signature_version s3v4",
        )
        self.assertEqual(
            "[default]\n"
            "region = us-west-2\n"
            "ec2 =\n"
            "    signature_version = v4\n"
            "s3 =\n"
            "    signature_version = s3v4\n",
            self.get_config_file_contents(),
        )

    def test_set_with_new_profile(self):
        self.set_config_file_contents(
            "[default]\n"
            "s3 =\n"
            "    signature_version = s3v4\n"
        )
        self.run_cmd(
            "configure set profile.dev.s3.signature_version s3v4",
        )
        self.assertEqual(
            "[default]\n"
            "s3 =\n"
            "    signature_version = s3v4\n"
            "[profile dev]\n"
            "s3 =\n"
            "    signature_version = s3v4\n",
            self.get_config_file_contents(),
        )

    def test_override_existing_value(self):
        self.set_config_file_contents(
            "[default]\n" "s3 =\n"
            "    signature_version = v4\n"
        )
        self.run_cmd(
            "configure set default.s3.signature_version NEWVALUE",
        )
        self.assertEqual(
            "[default]\n"
            "s3 =\n"
            "    signature_version = NEWVALUE\n",
            self.get_config_file_contents(),
        )

    def test_get_nested_attribute(self):
        self.set_config_file_contents(
            "[default]\n"
            "s3 =\n"
            "    signature_version = v4\n"
        )
        stdout, _, _ = self.run_cmd(
            "configure get default.s3.signature_version"
        )

        self.assertEqual(stdout.strip(), "v4")
        stdout, _, _ = self.run_cmd(
            "configure get default.bad.doesnotexist", expected_rc=1
        )
        self.assertEqual(stdout, "")

    def test_can_handle_empty_section(self):
        self.set_config_file_contents("[default]\n")
        self.run_cmd(
            "configure set preview.cloudfront true",
        )
        self.run_cmd(
            "configure set region us-west-2",
        )
        self.assertEqual(
            "[default]\n"
            "region = us-west-2\n"
            "[preview]\n"
            "cloudfront = true\n",
            self.get_config_file_contents(),
        )


class TestConfigureHasArgTable(unittest.TestCase):
    def test_configure_command_has_arg_table(self):
        m = mock.Mock()
        command = ConfigureCommand(m)
        self.assertEqual(command.arg_table, {})
