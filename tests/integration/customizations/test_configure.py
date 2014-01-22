# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests import unittest
import os
import tempfile
import random

from tests.integration import aws


class TestConfigureCommand(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
        self.config_filename = os.path.join(
            self.tempdir, 'config-%s' % random.randint(1, 100000))
        self.env_vars = os.environ.copy()
        self.env_vars['AWS_CONFIG_FILE'] = self.config_filename

    def tearDown(self):
        if os.path.isfile(self.config_filename):
            os.remove(self.config_filename)
        os.rmdir(self.tempdir)

    def set_config_file_contents(self, contents):
        with open(self.config_filename, 'w') as f:
            f.write(contents)

    def get_config_file_contents(self):
        with open(self.config_filename, 'r') as f:
            return f.read()

    def test_list_command(self):
        self.set_config_file_contents(
            '\n'
            '[default]\n'
            'aws_access_key_id=12345\n'
            'aws_secret_access_key=12345\n'
            'region=us-west-2\n'
        )
        self.env_vars.pop('AWS_DEFAULT_REGION', None)
        self.env_vars.pop('AWS_ACCESS_KEY_ID', None)
        self.env_vars.pop('AWS_SECRET_ACCESS_KEY', None)
        p = aws('configure list', env_vars=self.env_vars)
        self.assertRegexpMatches(p.stdout, r'access_key.+config_file')
        self.assertRegexpMatches(p.stdout, r'secret_key.+config_file')
        self.assertRegexpMatches(p.stdout, r'region\s+us-west-2\s+config_file')

    def test_get_command(self):
        self.set_config_file_contents(
            '\n'
            '[default]\n'
            'aws_access_key_id=access_key\n'
            'aws_secret_access_key=secret_key\n'
            'region=us-west-2\n'
        )
        p = aws('configure get aws_access_key_id', env_vars=self.env_vars)
        self.assertEqual(p.stdout.strip(), 'access_key')

    def test_get_command_with_profile_set(self):
        self.set_config_file_contents(
            '\n'
            '[default]\n'
            'aws_access_key_id=default_access_key\n'
            '\n'
            '[profile testing]\n'
            'aws_access_key_id=testing_access_key\n'
        )
        p = aws('configure get aws_access_key_id --profile testing',
                env_vars=self.env_vars)
        self.assertEqual(p.stdout.strip(), 'testing_access_key')

    def test_get_with_fq_name(self):
        # test get configs with fully qualified name.
        self.set_config_file_contents(
            '\n'
            '[default]\n'
            'aws_access_key_id=default_access_key\n'
            '\n'
            '[profile testing]\n'
            'aws_access_key_id=testing_access_key\n'
        )
        p = aws('configure get default.aws_access_key_id --profile testing',
                env_vars=self.env_vars)
        self.assertEqual(p.stdout.strip(), 'default_access_key')

    def test_get_with_fq_profile_name(self):
        self.set_config_file_contents(
            '\n'
            '[default]\n'
            'aws_access_key_id=default_access_key\n'
            '\n'
            '[profile testing]\n'
            'aws_access_key_id=testing_access_key\n'
        )
        p = aws('configure get profile.testing.aws_access_key_id --profile default',
                env_vars=self.env_vars)
        self.assertEqual(p.stdout.strip(), 'testing_access_key')

    def test_get_fq_with_quoted_profile_name(self):
        self.set_config_file_contents(
            '\n'
            '[default]\n'
            'aws_access_key_id=default_access_key\n'
            '\n'
            '[profile "testing"]\n'
            'aws_access_key_id=testing_access_key\n'
        )
        p = aws('configure get profile.testing.aws_access_key_id --profile default',
                env_vars=self.env_vars)
        self.assertEqual(p.stdout.strip(), 'testing_access_key')

    def test_get_fq_for_non_profile_configs(self):
        self.set_config_file_contents(
            '\n'
            '[default]\n'
            'aws_access_key_id=default_access_key\n'
            '\n'
            '[profile testing]\n'
            'aws_access_key_id=testing_access_key\n'
            '[preview]\n'
            'emr=true'
        )
        p = aws('configure get preview.emr --profile default',
                env_vars=self.env_vars)
        self.assertEqual(p.stdout.strip(), 'true')

    def test_set_with_config_file_no_exist(self):
        aws('configure set region us-west-1', env_vars=self.env_vars)
        self.assertEqual(
            '[default]\n'
            'region = us-west-1\n', self.get_config_file_contents())

    def test_set_with_empty_config_file(self):
        with open(self.config_filename, 'w'):
            pass

        aws('configure set region us-west-1', env_vars=self.env_vars)
        self.assertEqual(
            '[default]\n'
            'region = us-west-1\n', self.get_config_file_contents())

    def test_set_with_updating_value(self):
        self.set_config_file_contents(
            '[default]\n'
            'region = us-west-2\n')

        aws('configure set region us-west-1', env_vars=self.env_vars)
        self.assertEqual(
            '[default]\n'
            'region = us-west-1\n', self.get_config_file_contents())

    def test_set_with_profile(self):
        aws('configure set region us-west-1 --profile testing',
            env_vars=self.env_vars)
        self.assertEqual(
            '[profile testing]\n'
            'region = us-west-1\n', self.get_config_file_contents())

    def test_set_with_fq_single_dot(self):
        aws('configure set preview.cloudsearch true', env_vars=self.env_vars)
        self.assertEqual(
            '[preview]\n'
            'cloudsearch = true\n', self.get_config_file_contents())

    def test_set_with_fq_double_dot(self):
        aws('configure set profile.testing.region us-west-2',
            env_vars=self.env_vars)
        self.assertEqual(
            '[profile testing]\n'
            'region = us-west-2\n', self.get_config_file_contents())

    def test_set_with_commented_out_field(self):
        self.set_config_file_contents(
            '#[preview]\n'
            ';cloudsearch = true\n')
        aws('configure set preview.cloudsearch true', env_vars=self.env_vars)
        self.assertEqual(
            '#[preview]\n'
            ';cloudsearch = true\n'
            '[preview]\n'
            'cloudsearch = true\n', self.get_config_file_contents())


if __name__ == '__main__':
    unittest.main()
