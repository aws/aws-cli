# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import ruamel.yaml as yaml


from awscli.testutils import skip_if_windows, if_windows
from awscli.testutils import mock, create_clidriver, FileCreator
from awscli.testutils import BaseAWSCommandParamsTest


class TestOutput(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestOutput, self).setUp()
        self.files = FileCreator()

        self.patch_popen = mock.patch('awscli.utils.Popen')
        self.mock_popen = self.patch_popen.start()

        self.patch_tty = mock.patch('awscli.utils.is_a_tty')
        self.mock_is_a_tty = self.patch_tty.start()
        self.mock_is_a_tty.return_value = True

        self.cmdline = 'ec2 describe-regions'
        self.parsed_response = {
            "Regions": [
                {
                        "Endpoint": "ec2.ap-south-1.amazonaws.com",
                        "RegionName": "ap-south-1"
                },
            ]
        }
        self.expected_content = self.get_expected_content(self.parsed_response)

    def tearDown(self):
        super(TestOutput, self).tearDown()
        self.files.remove_all()
        self.patch_popen.stop()
        self.patch_tty.stop()

    def get_expected_content(self, response):
        content = json.dumps(response, indent=4)
        content += '\n'
        return content

    def write_cli_pager_config(self, pager):
        config_file = self.files.create_file(
            'config',
            '[default]\n'
            'cli_pager = %s\n' % pager
        )
        self.environ['AWS_CONFIG_FILE'] = config_file
        self.driver = create_clidriver()

    def assert_content_to_pager(self, expected_pager, expected_content,
                                expected_less_flags=None):
        actual_pager = self.mock_popen.call_args[1]['args']
        if isinstance(actual_pager, list):
            actual_pager = ' '.join(actual_pager)
        self.assertEqual(expected_pager, actual_pager)
        self.assertEqual(expected_content, self.get_content_sent_to_popen())
        if expected_less_flags:
            actual_env = self.mock_popen.call_args[1]['env']
            self.assertEqual(expected_less_flags, actual_env['LESS'])

    def get_content_sent_to_popen(self):
        content = ''
        popen_stdin = self.mock_popen.return_value.stdin
        for write_call in popen_stdin.write.call_args_list:
            content += write_call[0][0]
        return content

    def test_outputs_to_pager(self):
        self.run_cmd(self.cmdline)
        self.assert_content_to_pager(
            expected_pager=mock.ANY,
            expected_content=self.expected_content
        )

    def test_does_not_output_to_pager_if_not_tty(self):
        self.mock_is_a_tty.return_value = False
        stdout, _, _ = self.run_cmd(self.cmdline)
        self.assertFalse(self.mock_popen.called)
        self.assertEqual(stdout, self.expected_content)

    @skip_if_windows('less is not used for windows')
    def test_outputs_to_less_non_windows(self):
        self.run_cmd(self.cmdline)
        self.assert_content_to_pager(
            expected_pager='less',
            expected_content=self.expected_content,
            expected_less_flags='FRX'
        )

    @if_windows('more is only used for windows')
    def test_outputs_to_more_for_windows(self):
        self.run_cmd(self.cmdline)
        self.assert_content_to_pager(
            expected_pager='more',
            expected_content=self.expected_content,
        )

    def test_respects_aws_pager_env_var(self):
        self.environ['AWS_PAGER'] = 'mypager'
        self.run_cmd(self.cmdline)
        self.assert_content_to_pager(
            expected_pager='mypager',
            expected_content=self.expected_content,
        )

    def test_respects_cli_pager_config_var(self):
        self.write_cli_pager_config('mypager')
        self.run_cmd(self.cmdline)
        self.assert_content_to_pager(
            expected_pager='mypager',
            expected_content=self.expected_content,
        )

    def test_respects_pager_env_var(self):
        self.environ['PAGER'] = 'mypager'
        self.run_cmd(self.cmdline)
        self.assert_content_to_pager(
            expected_pager='mypager',
            expected_content=self.expected_content,
        )

    def test_no_pager_if_configured_to_empty_str(self):
        self.environ['AWS_PAGER'] = ''
        stdout, _, _ = self.run_cmd(self.cmdline)
        self.assertFalse(self.mock_popen.called)
        self.assertEqual(stdout, self.expected_content)

    def test_aws_pager_env_var_beats_cli_pager_config_var(self):
        self.environ['AWS_PAGER'] = 'envpager'
        self.write_cli_pager_config('configpager')
        self.run_cmd(self.cmdline)
        self.assert_content_to_pager(
            expected_pager='envpager',
            expected_content=self.expected_content,
        )

    def test_aws_pager_env_var_beats_pager_env_var(self):
        self.write_cli_pager_config('configpager')
        self.environ['PAGER'] = 'envpager'
        self.run_cmd(self.cmdline)
        self.assert_content_to_pager(
            expected_pager='configpager',
            expected_content=self.expected_content,
        )

    def test_cli_pager_config_var_beats_pager_env_var(self):
        self.environ['AWS_PAGER'] = 'awspager'
        self.environ['PAGER'] = 'envpager'
        self.run_cmd(self.cmdline)
        self.assert_content_to_pager(
            expected_pager='awspager',
            expected_content=self.expected_content,
        )

    def test_respects_less_env_var(self):
        self.environ['AWS_PAGER'] = 'less'
        self.environ['LESS'] = 'S'
        self.run_cmd(self.cmdline)
        self.assert_content_to_pager(
            expected_pager='less',
            expected_content=self.expected_content,
            expected_less_flags='S'
        )


class TestYAMLStream(BaseAWSCommandParamsTest):
    def assert_yaml_response_equal(self, response, expected):
        with self.assertRaises(ValueError):
            json.loads(response)
        loaded = yaml.safe_load(response)
        self.assertEqual(loaded, expected)

    def test_yaml_stream_single_response(self):
        cmdline = 'dynamodb list-tables --output yaml-stream --no-paginate'
        self.parsed_responses = [
            {
                'TableNames': [
                    'MyTable'
                ]
            }
        ]
        stdout, _, _ = self.run_cmd(cmdline)
        self.assert_yaml_response_equal(
            stdout,
            [
                {'TableNames': ['MyTable']}
            ]
        )

    def test_yaml_stream_paginated_response(self):
        cmdline = 'dynamodb list-tables --output yaml-stream'
        self.parsed_responses = [
            {
                'TableNames': [
                    'MyTable'
                ],
                'LastEvaluatedTableName': 'MyTable'
            },
            {
                'TableNames': [
                    'MyTable2'
                ]
            },
        ]
        stdout, _, _ = self.run_cmd(cmdline)
        self.assert_yaml_response_equal(
            stdout,
            [
                {
                    'TableNames': [
                        'MyTable'
                    ],
                    'LastEvaluatedTableName': 'MyTable'
                },
                {
                    'TableNames': [
                        'MyTable2'
                    ]
                },
            ]
        )

    def test_yaml_stream_removes_response_metadata(self):
        cmdline = 'dynamodb list-tables --output yaml-stream --no-paginate'
        self.parsed_responses = [
            {
                'TableNames': [
                    'MyTable'
                ],
                'ResponseMetadata': {'RequestId': 'id'}
            }
        ]
        stdout, _, _ = self.run_cmd(cmdline)
        self.assert_yaml_response_equal(
            stdout,
            [
                {'TableNames': ['MyTable']}
            ]
        )

    def test_yaml_stream_removes_response_metadata_for_all_responses(self):
        cmdline = 'dynamodb list-tables --output yaml-stream'
        self.parsed_responses = [
            {
                'TableNames': [
                    'MyTable'
                ],
                'LastEvaluatedTableName': 'MyTable',
                'ResponseMetadata': {'RequestId': 'id'}
            },
            {
                'TableNames': [
                    'MyTable2'
                ],
                'ResponseMetadata': {'RequestId': 'id2'}
            },
        ]
        stdout, _, _ = self.run_cmd(cmdline)
        self.assert_yaml_response_equal(
            stdout,
            [
                {
                    'TableNames': [
                        'MyTable'
                    ],
                    'LastEvaluatedTableName': 'MyTable'
                },
                {
                    'TableNames': [
                        'MyTable2'
                    ]
                },
            ]
        )

    def test_yaml_stream_uses_query(self):
        cmdline = (
            'dynamodb list-tables --output yaml-stream --no-paginate '
            '--query TableNames'
        )
        self.parsed_responses = [
            {
                'TableNames': [
                    'MyTable'
                ]
            }
        ]
        stdout, _, _ = self.run_cmd(cmdline)
        self.assert_yaml_response_equal(
            stdout,
            [
                ['MyTable']
            ]
        )

    def test_yaml_stream_uses_query_across_each_response(self):
        cmdline = (
            'dynamodb list-tables --output yaml-stream --query TableNames'
        )
        self.parsed_responses = [
            {
                'TableNames': [
                    'MyTable'
                ],
                'LastEvaluatedTableName': 'MyTable'
            },
            {
                'TableNames': [
                    'MyTable2'
                ]
            },
        ]
        stdout, _, _ = self.run_cmd(cmdline)
        self.assert_yaml_response_equal(
            stdout,
            [
                ['MyTable'],
                ['MyTable2']
            ]
        )

    def test_yaml_stream_with_empty_response(self):
        cmdline = (
            's3api delete-bucket --bucket mybucket --output yaml-stream'
        )
        self.parsed_responses = [{}]
        stdout, _, _ = self.run_cmd(cmdline)
        self.assertEqual(stdout, '')
