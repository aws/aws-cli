# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import pytest

import botocore.session
from botocore.exceptions import ParamValidationError
from botocore.stub import Stubber

ALIAS_CASES = [
    {
        'service': 'ec2',
        'operation': 'describe_flow_logs',
        'original_name': 'Filter',
        'new_name': 'Filters',
        'parameter_value': [{'Name': 'traffic-type', 'Values': ['ACCEPT']}],
    },
    {
        'service': 'cloudsearchdomain',
        'operation': 'search',
        'original_name': 'return',
        'new_name': 'returnFields',
        'parameter_value': '_all_fields',
        'extra_args': {'query': 'foo'},
    },
    {
        'service': 'logs',
        'operation': 'create_export_task',
        'original_name': 'from',
        'new_name': 'fromTime',
        'parameter_value': 0,
        'extra_args': {
            'logGroupName': 'name',
            'to': 10,
            'destination': 'mybucket',
        },
    },
]


@pytest.mark.parametrize("case", ALIAS_CASES)
def test_can_use_alias(case):
    session = botocore.session.get_session()
    _can_use_parameter_in_client_call(session, case)


@pytest.mark.parametrize("case", ALIAS_CASES)
def test_can_use_original_name(case):
    session = botocore.session.get_session()
    _can_use_parameter_in_client_call(session, case, False)


def _can_use_parameter_in_client_call(session, case, use_alias=True):
    client = session.create_client(
        case['service'],
        region_name='us-east-1',
        aws_access_key_id='foo',
        aws_secret_access_key='bar',
    )

    stubber = Stubber(client)
    stubber.activate()
    operation = case['operation']
    params = case.get('extra_args', {})
    params = params.copy()
    param_name = case['original_name']
    if use_alias:
        param_name = case['new_name']
    params[param_name] = case['parameter_value']
    stubbed_response = case.get('stubbed_response', {})
    stubber.add_response(operation, stubbed_response)
    try:
        getattr(client, operation)(**params)
    except ParamValidationError as e:
        raise AssertionError(
            'Expecting {} to be valid parameter for {}.{} but received '
            '{}.'.format(
                case['new_name'], case['service'], case['operation'], e
            )
        )
