# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import json
import os
from datetime import datetime, timedelta

from dateutil.tz import tzutc

import awscli.clidriver
from awscli.customizations import assumerole
from awscli.customizations.configure.exportcreds import (
    ConfigureExportCredentialsCommand,
)
from awscli.testutils import (
    BaseAWSCommandParamsTest,
    create_clidriver,
    mock,
)


class TestExportCredentialsCredentialCache(BaseAWSCommandParamsTest):
    def setUp(self):
        super().setUp()
        # Role profiles only; keep env credentials out of the chain.
        del self.environ['AWS_ACCESS_KEY_ID']
        del self.environ['AWS_SECRET_ACCESS_KEY']
        self.config_file = os.path.join(self._config_dir, 'config')
        self.cache_dir = os.path.join(self._config_dir, 'cli-cache')
        cache_dir_patch = mock.patch.object(
            assumerole, 'CACHE_DIR', self.cache_dir
        )
        cache_dir_patch.start()
        self.addCleanup(cache_dir_patch.stop)

    def write_config(self, extra=''):
        with open(self.config_file, 'w') as f:
            f.write(
                '[profile A]\n'
                'role_arn = arn:aws:iam::123456789012:role/RoleA\n'
                'source_profile = B\n'
                f'{extra}\n'
                '[profile B]\n'
                'aws_access_key_id = abc123\n'
                'aws_secret_access_key = def456\n'
            )

    def assume_role_response(self, access_key):
        return {
            'Credentials': {
                'AccessKeyId': access_key,
                'SecretAccessKey': 'secret',
                'SessionToken': 'token',
                'Expiration': datetime.now(tzutc()) + timedelta(hours=1),
            },
            'AssumedRoleUser': {
                'AssumedRoleId': 'roleid',
                'Arn': 'arn:aws:sts::123456789012:assumed-role/RoleA/s',
            },
        }

    def export_credentials(self, access_key):
        # A new driver per command, as each aws invocation is a new process.
        # The command records its profile in the environment to catch
        # recursion; a new process wouldn't inherit it from a sibling.
        self.environ.pop(
            ConfigureExportCredentialsCommand._RECURSION_VAR, None
        )
        self.driver = create_clidriver()
        self.entry_point = awscli.clidriver.AWSCLIEntryPoint(self.driver)
        self.parsed_responses = [self.assume_role_response(access_key)]
        stdout, _, _ = self.run_cmd(
            'configure export-credentials --profile A --format process'
        )
        return json.loads(stdout)

    def assume_role_calls(self):
        return [
            model.name
            for model, _ in self.operations_called
            if model.name == 'AssumeRole'
        ]

    def cache_files(self):
        if not os.path.isdir(self.cache_dir):
            return []
        return os.listdir(self.cache_dir)

    def test_memory_profile_writes_no_cache_file(self):
        self.write_config('credential_cache = memory\n')
        first = self.export_credentials('first')
        second = self.export_credentials('second')
        self.assertEqual(first['AccessKeyId'], 'first')
        self.assertEqual(second['AccessKeyId'], 'second')
        self.assertEqual(len(self.assume_role_calls()), 2)
        self.assertEqual(self.cache_files(), [])

    def test_default_profile_writes_cache_file(self):
        self.write_config()
        first = self.export_credentials('first')
        second = self.export_credentials('second')
        self.assertEqual(first['AccessKeyId'], 'first')
        # The second command reads the cache file instead of calling STS.
        self.assertEqual(second['AccessKeyId'], 'first')
        self.assertEqual(len(self.assume_role_calls()), 1)
        self.assertEqual(len(self.cache_files()), 1)
