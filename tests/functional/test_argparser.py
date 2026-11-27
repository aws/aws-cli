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
import pytest

from tests import CLIRunner


def test_unknown_option_lists_service_options():
    result = CLIRunner().run(
        ['cloudwatch', 'describe-alarms', '--include-composite-alarms']
    )

    assert result.rc == 252
    assert 'Unknown options: --include-composite-alarms' in result.stderr
    assert result.stderr.endswith(
        'Valid options for this command:\n'
        '  --alarm-names, --alarm-name-prefix, --alarm-types, '
        '--children-of-alarm-name,\n'
        '  --parents-of-alarm-name, --state-value, --action-prefix\n'
    )
    assert result.aws_requests == []


def test_unknown_option_lists_custom_command_options():
    result = CLIRunner().run(['configure', 'export-credentials', '--unknown'])

    assert result.rc == 252
    assert 'Unknown options: --unknown' in result.stderr
    assert result.stderr.endswith(
        'Valid options for this command:\n  --format\n'
    )
    assert result.aws_requests == []


def test_unknown_option_lists_service_max_items():
    result = CLIRunner().run(
        [
            'wafv2',
            'get-sampled-requests',
            '--cli-input-json',
            '{}',
            '--unknown',
        ]
    )

    assert result.rc == 252
    assert 'Unknown options: --unknown' in result.stderr
    assert result.stderr.endswith(
        'Valid options for this command:\n'
        '  --web-acl-arn, --rule-metric-name, --scope, --time-window, '
        '--max-items\n'
    )
    assert result.aws_requests == []


def test_unknown_option_combines_service_boolean_options():
    result = CLIRunner().run(['ec2', 'describe-instances', '--unknown'])

    assert result.rc == 252
    assert 'Valid options for this command:\n' in result.stderr
    assert '--[no-]dry-run' in result.stderr
    assert '--no-dry-run' not in result.stderr
    assert result.aws_requests == []


def test_unknown_option_does_not_list_many_options():
    result = CLIRunner().run(['s3', 'cp', 'a', 's3://b/c', '--tagging', 'k=v'])

    assert result.rc == 252
    assert 'Unknown options:' in result.stderr
    assert 'Valid options for this command:' not in result.stderr
    assert result.aws_requests == []
