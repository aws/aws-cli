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
"""Autocompletion for the ``service`` argument of ``aws console``."""
from awscli.autocomplete.completer import BaseCompleter, CompletionResult
from awscli.autocomplete.filters import startswith_filter

# Common service slugs to suggest for ``aws console <service>``. This is a
# convenience list, not an exhaustive one: any service name is accepted, and
# ``--destination`` can be used for an exact URL.
_COMMON_SERVICES = [
    'apigateway',
    'athena',
    'cloudformation',
    'cloudfront',
    'cloudtrail',
    'cloudwatch',
    'dynamodb',
    'ec2',
    'ecr',
    'ecs',
    'eks',
    'elasticache',
    'events',
    'iam',
    'kms',
    'lambda',
    'logs',
    'rds',
    'route53',
    's3',
    'secretsmanager',
    'sns',
    'sqs',
    'ssm',
    'stepfunctions',
    'vpc',
]


def add_console_completers(custom_completers):
    custom_completers.append(ConsoleServiceCompleter())


class ConsoleServiceCompleter(BaseCompleter):
    def complete(self, parsed):
        if (
            parsed.current_command == 'console'
            and parsed.current_param == 'service'
            and parsed.current_fragment is not None
        ):
            return startswith_filter(
                parsed.current_fragment,
                [CompletionResult(name=s) for s in _COMMON_SERVICES],
            )
        return None
