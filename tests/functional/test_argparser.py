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
from tests import CLIRunner

EXPECTED_FOOTER = (
    'usage: aws [options] <command> <subcommand> [<subcommand> ...] '
    '[parameters]\n'
    'To see help text, you can run:\n'
    '\n'
    '  aws help\n'
    '  aws <command> help\n'
    '  aws <command> <subcommand> help\n'
)


def test_invalid_operation_suggests_spelling_matches():
    result = CLIRunner().run(['s3api', 'list-objecst'])
    assert result.rc == 252
    assert (
        result.stderr
        == (
            '\n'
            'aws: [ERROR]: An error occurred (ParamValidation): argument '
            "operation: Found invalid choice 'list-objecst'\n"
            '\n'
            'Maybe you meant:\n'
            '\n'
            '  * list-objects\n'
            '  * list-objects-v2\n'
            '\n'
        )
        + EXPECTED_FOOTER
    )


def test_invalid_operation_suggests_verb_swaps():
    result = CLIRunner().run(['glue', 'list-tables'])
    assert result.rc == 252
    assert (
        result.stderr
        == (
            '\n'
            'aws: [ERROR]: An error occurred (ParamValidation): argument '
            "operation: Found invalid choice 'list-tables'\n"
            '\n'
            'Maybe you meant:\n'
            '\n'
            '  * get-tables\n'
            '  * search-tables\n'
            '  * get-table\n'
            '\n'
        )
        + EXPECTED_FOOTER
    )
