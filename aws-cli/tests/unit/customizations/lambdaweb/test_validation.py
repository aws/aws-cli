# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import argparse
from unittest import mock

import pytest

from awscli.customizations.lambdaweb import constants, validation
from awscli.customizations.lambdaweb.exceptions import (
    InvalidArgumentValueError,
    InvalidKeyValueError,
    InvalidSourceError,
    LambdaWebError,
)

_ENV_KEY_PATTERN = r'[a-zA-Z]([a-zA-Z0-9_])*'


def _parsed_args(**overrides):
    values = {
        'env': None,
        'timeout_seconds': None,
        'max_concurrency_per_environment': None,
        'activation_timeout': constants.DEFAULT_ACTIVATION_TIMEOUT_SECONDS,
        'progress_frequency': None,
        'endpoint_type': None,
        'auto_deployment_mode': None,
        'regions': None,
    }
    for name in validation.args.INT_ARG_VALIDATION:
        values.setdefault(name, None)
    values.update(overrides)
    return argparse.Namespace(**values)


def test_normalize_args_skips_model_lookup_without_env():
    with mock.patch.object(validation.model, 'string_pattern') as pattern:
        normalized = validation.normalize_args(
            mock.sentinel.session,
            _parsed_args(),
        )

    assert normalized.env == {}
    pattern.assert_not_called()


def test_normalize_args_preserves_equals_in_value():
    with mock.patch.object(
        validation.model,
        'string_pattern',
        return_value=_ENV_KEY_PATTERN,
    ):
        normalized = validation.normalize_args(
            mock.sentinel.session,
            _parsed_args(env=['TOKEN=a=b=c']),
        )

    assert normalized.env == {'TOKEN': 'a=b=c'}


def test_split_regions_trims_deduplicates_and_preserves_order():
    assert validation._split_regions(
        ' us-east-1,us-west-2, us-east-1 ,, '
    ) == ['us-east-1', 'us-west-2']


@pytest.mark.parametrize('entry', ['==========', '=value'])
def test_normalize_args_rejects_empty_key(entry):
    with pytest.raises(InvalidKeyValueError, match='key must not be empty'):
        validation.normalize_args(
            mock.sentinel.session,
            _parsed_args(env=[entry]),
        )


@pytest.mark.parametrize('entry', ['1BAD=value', 'BAD-NAME=value'])
def test_normalize_args_rejects_invalid_key(entry):
    with (
        mock.patch.object(
            validation.model,
            'string_pattern',
            return_value=_ENV_KEY_PATTERN,
        ),
        pytest.raises(
            InvalidKeyValueError,
            match='not a valid environment variable name',
        ),
    ):
        validation.normalize_args(
            mock.sentinel.session,
            _parsed_args(env=[entry]),
        )


def test_normalize_args_rejects_empty_value():
    with pytest.raises(InvalidKeyValueError, match='must not be empty'):
        validation.normalize_args(
            mock.sentinel.session,
            _parsed_args(env=['KEY=']),
        )


@pytest.mark.parametrize(
    'revision',
    [
        {},
        {'serviceConfig': {'environmentVariables': {}}},
        {
            'errors': [
                {
                    'attribute': 'buildConfig.runtimeConfig',
                    'errorCode': 'SomeOtherError',
                    'errorMessage': 'Unrelated revision error.',
                }
            ]
        },
    ],
)
def test_reject_unreadable_environment_allows_no_matching_error(revision):
    validation.reject_unreadable_environment('my-fn', revision)


def test_reject_unreadable_environment_reports_matching_error():
    revision = {
        'errors': [
            {
                'attribute': 'buildConfig.runtimeConfig',
                'errorCode': 'SomeOtherError',
                'errorMessage': 'Unrelated revision error.',
            },
            {
                'attribute': 'serviceConfig.environmentVariables',
                'errorCode': 'AccessDeniedException',
                'errorMessage': 'Could not decrypt the environment variables',
            },
        ]
    }

    with pytest.raises(LambdaWebError) as excinfo:
        validation.reject_unreadable_environment('my-fn', revision)

    message = str(excinfo.value)
    assert "Web Function 'my-fn'" in message
    assert 'AccessDeniedException' in message
    assert 'Could not decrypt the environment variables.' in message
    assert 'run the command again' in message


def test_verify_entrypoint_accepts_existing_file(tmp_path):
    entrypoint = tmp_path / 'server.js'
    entrypoint.write_text('export default {};\n')

    validation.verify_entrypoint_in_tree(str(tmp_path), 'server.js')


def test_verify_entrypoint_rejects_missing_file(tmp_path):
    with pytest.raises(InvalidSourceError, match='no such file'):
        validation.verify_entrypoint_in_tree(str(tmp_path), 'server.js')


def test_verify_entrypoint_warns_for_uncertain_path(tmp_path, capsys):
    validation.verify_entrypoint_in_tree(str(tmp_path), '../server.js')

    assert 'Warning:' in capsys.readouterr().err


@pytest.mark.parametrize(
    ('field', 'value', 'flag'),
    [
        ('activation_timeout', 0, '--activation-timeout'),
        ('progress_frequency', -1, '--progress-frequency'),
    ],
)
def test_validate_bounded_args_rejects_nonpositive_cli_timeout(
    field,
    value,
    flag,
):
    parsed_args = _parsed_args(**{field: value})
    normalized = validation.normalize_args(
        mock.sentinel.session,
        parsed_args,
    )
    with (
        mock.patch.object(validation, 'validate_int_in_model_range'),
        pytest.raises(InvalidArgumentValueError, match=flag),
    ):
        validation.validate_bounded_args(
            mock.sentinel.session,
            parsed_args,
            normalized,
        )


@pytest.mark.parametrize('endpoint_type', ['MultiRegion', 'PerRegion'])
def test_region_endpoint_requires_region_outside_home(endpoint_type):
    parsed_args = _parsed_args(
        endpoint_type=endpoint_type,
        regions='us-east-1',
    )
    normalized = validation.normalize_args(
        mock.sentinel.session,
        parsed_args,
    )

    with pytest.raises(LambdaWebError, match='other than the home Region'):
        validation.validate_create_endpoint_args(
            parsed_args,
            normalized,
            'us-east-1',
        )


def test_home_region_endpoint_rejects_other_regions():
    parsed_args = _parsed_args(
        endpoint_type='HomeRegion',
        regions='us-west-2',
    )
    normalized = validation.normalize_args(
        mock.sentinel.session,
        parsed_args,
    )

    with pytest.raises(LambdaWebError, match='only the home Region'):
        validation.validate_create_endpoint_args(
            parsed_args,
            normalized,
            'us-east-1',
        )


@pytest.mark.parametrize(
    ('endpoint_type', 'regions'),
    [
        ('HomeRegion', 'us-east-1'),
        ('MultiRegion', 'us-west-2'),
        ('PerRegion', 'us-east-1,us-west-2'),
    ],
)
def test_create_endpoint_accepts_valid_region_sets(endpoint_type, regions):
    parsed_args = _parsed_args(
        endpoint_type=endpoint_type,
        regions=regions,
    )
    normalized = validation.normalize_args(
        mock.sentinel.session,
        parsed_args,
    )

    validation.validate_create_endpoint_args(
        parsed_args,
        normalized,
        'us-east-1',
    )


def test_immutable_regions_error_leads_with_nondestructive_recovery():
    parsed_args = _parsed_args(regions='us-east-1,us-west-2')
    normalized = validation.normalize_args(
        mock.sentinel.session,
        parsed_args,
    )
    target = {
        'endpointName': 'production',
        'endpointType': 'MultiRegion',
        'regions': ['us-east-1', 'eu-west-1'],
    }

    with pytest.raises(LambdaWebError) as excinfo:
        validation.reject_immutable_endpoint_args(
            parsed_args,
            normalized,
            target,
        )

    message = str(excinfo.value)
    assert "endpoint 'production'" in message
    assert "existing endpoint wasn't changed" in message
    assert 'AWS Regions you specified' in message
    assert message.index('create a new endpoint') < message.index('delete it')
