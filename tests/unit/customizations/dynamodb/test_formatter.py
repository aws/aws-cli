# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from argparse import Namespace
from decimal import Decimal

import jmespath
import pytest

from awscli.customizations.dynamodb.formatter import DynamoYAMLDumper
from awscli.customizations.dynamodb.types import Binary
from awscli.formatter import YAMLFormatter
from awscli.testutils import capture_output


@pytest.mark.parametrize(
    'case',
    [
        {
            'given': {'mykey': Decimal('1')},
            'expected': '1\n',
            'query': 'mykey',
        },
        {
            'given': {'mykey': Decimal('1.1')},
            'expected': '1.1\n',
            'query': 'mykey',
        },
        {
            'given': {'mykey': Decimal('1')},
            'expected': 'mykey: 1\n',
        },
        {
            'given': {'mykey': Decimal('1.1')},
            'expected': 'mykey: 1.1\n',
        },
        {
            'given': {'mykey': Binary(b'\xae\x85\x8b\xd7')},
            'expected': 'mykey: !!binary "roWL1w=="\n',
        },
        {
            'given': {'mykey': Binary(b'\xae\x85\x8b\xd7')},
            'expected': '!!binary "roWL1w=="\n',
            'query': 'mykey',
        },
    ],
)
def test_yaml_formatter_with_dynamo_dumper(case):
    compiled_query = None
    if case.get('query') is not None:
        compiled_query = jmespath.compile(case['query'])
    formatter = YAMLFormatter(
        Namespace(query=compiled_query), DynamoYAMLDumper()
    )
    with capture_output() as output:
        formatter('fake-command-name', case['given'])
    assert output.stdout.getvalue() == case['expected']
