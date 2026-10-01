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
from types import SimpleNamespace
from unittest import mock

import botocore.session
from botocore.validate import validate_parameters

from awscli.customizations.lambdaweb import constants, model, requests


def _shape(type_name, **kwargs):
    shape = SimpleNamespace(type_name=type_name, **kwargs)
    if type_name == 'structure':
        shape.is_document_type = False
        shape.is_tagged_union = False
    return shape


def test_copy_input_fields_recurses_and_filters_response_fields():
    scalar = _shape('string')
    nested = _shape(
        'structure',
        members={
            'existing': scalar,
            'futureNested': scalar,
        },
    )
    list_member = _shape(
        'structure',
        members={'value': scalar},
    )
    map_value = _shape(
        'structure',
        members={'enabled': scalar},
    )
    document = _shape('structure')
    document.is_document_type = True
    input_shape = _shape(
        'structure',
        members={
            'existingTopLevel': scalar,
            'futureTopLevel': nested,
            'futureList': _shape('list', member=list_member),
            'futureMap': _shape('map', value=map_value),
            'futureDocument': document,
        },
    )
    operation = SimpleNamespace(input_shape=input_shape)
    service = mock.Mock()
    service.operation_model.return_value = operation
    session = mock.Mock()
    session.get_service_model.return_value = service
    source = {
        'existingTopLevel': 'keep',
        'futureTopLevel': {
            'existing': 'keep',
            'futureNested': '',
            'responseOnly': 'drop',
        },
        'futureList': [
            {'value': 'first', 'responseOnly': 'drop'},
            {'value': 'second'},
        ],
        'futureMap': {
            'one': {'enabled': False, 'responseOnly': 'drop'},
        },
        'futureDocument': {
            'unmodeledNestedValue': {'items': []},
        },
        'responseOnly': 'drop',
    }

    result = model.copy_input_fields(session, 'FutureOperation', source)

    assert result == {
        'existingTopLevel': 'keep',
        'futureTopLevel': {
            'existing': 'keep',
            'futureNested': '',
        },
        'futureList': [
            {'value': 'first'},
            {'value': 'second'},
        ],
        'futureMap': {
            'one': {'enabled': False},
        },
        'futureDocument': {
            'unmodeledNestedValue': {'items': []},
        },
    }
    source['futureTopLevel']['existing'] = 'changed'
    source['futureList'][0]['value'] = 'changed'
    source['futureDocument']['unmodeledNestedValue']['items'].append('changed')
    assert result['futureTopLevel']['existing'] == 'keep'
    assert result['futureList'][0]['value'] == 'first'
    assert result['futureDocument'] == {'unmodeledNestedValue': {'items': []}}
    session.get_service_model.assert_called_once_with(constants.SERVICE_NAME)
    service.operation_model.assert_called_once_with('FutureOperation')


_S3_OBJECT_PATH = ('buildConfig', 'codeConfig', 's3Object')


def _input_update_context():
    scalar = _shape('string')
    code_config = _shape(
        'structure',
        members={
            's3Object': scalar,
            'zipFile': scalar,
            'futureConfig': scalar,
        },
    )
    build_config = _shape(
        'structure',
        members={
            'codeConfig': code_config,
            'alternateBuild': scalar,
        },
    )
    input_shape = _shape(
        'structure',
        members={'buildConfig': build_config},
    )
    operation = SimpleNamespace(input_shape=input_shape)
    service = mock.Mock()
    service.operation_model.return_value = operation
    session = mock.Mock()
    session.get_service_model.return_value = service
    return session, build_config, code_config


def test_update_input_member_preserves_siblings_for_plain_structure():
    session, _, _ = _input_update_context()
    request = {
        'buildConfig': {
            'codeConfig': {
                'futureConfig': 'keep',
                's3Object': 'old',
            }
        }
    }
    model.update_input_member(
        session,
        'FutureOperation',
        _S3_OBJECT_PATH,
        request,
        lambda existing: f'{existing}-replacement',
    )
    assert request['buildConfig']['codeConfig'] == {
        'futureConfig': 'keep',
        's3Object': 'old-replacement',
    }


def test_update_input_member_creates_missing_path():
    session, _, _ = _input_update_context()
    request = {}
    update = mock.Mock(return_value='replacement')

    model.update_input_member(
        session,
        'FutureOperation',
        _S3_OBJECT_PATH,
        request,
        update,
    )
    assert request == {
        'buildConfig': {'codeConfig': {'s3Object': 'replacement'}}
    }
    update.assert_called_once_with(None)


def test_update_input_member_clears_siblings_for_tagged_union():
    session, _, code_config = _input_update_context()
    code_config.is_tagged_union = True
    request = {
        'buildConfig': {
            'codeConfig': {
                'zipFile': 'old',
            }
        }
    }
    model.update_input_member(
        session,
        'FutureOperation',
        _S3_OBJECT_PATH,
        request,
        lambda existing: 'replacement',
    )
    assert request['buildConfig']['codeConfig'] == {'s3Object': 'replacement'}


def test_update_input_member_clears_intermediate_union_siblings():
    session, build_config, _ = _input_update_context()
    build_config.is_tagged_union = True
    request = {
        'rootSibling': 'keep',
        'buildConfig': {
            'alternateBuild': 'drop',
            'codeConfig': {
                'futureConfig': 'keep',
                's3Object': 'old',
            },
        },
    }

    model.update_input_member(
        session,
        'FutureOperation',
        _S3_OBJECT_PATH,
        request,
        lambda existing: f'{existing}-replacement',
    )

    assert request == {
        'rootSibling': 'keep',
        'buildConfig': {
            'codeConfig': {
                'futureConfig': 'keep',
                's3Object': 'old-replacement',
            }
        },
    }


def _input_shape(session, operation_name):
    return (
        session.get_service_model(constants.SERVICE_NAME)
        .operation_model(operation_name)
        .input_shape
    )


def _endpoint_args():
    return SimpleNamespace(
        name='my-fn',
        endpoint_name=constants.DEFAULT_ENDPOINT_NAME,
        endpoint_type=None,
        auth_type='IamAuth',
        auto_deployment_mode=constants.DISABLED_AUTO_DEPLOYMENT_MODE,
        regions=None,
        description='updated',
        max_environments=2,
        rate_limit=0,
    )


def test_revision_request_matches_current_input_model():
    session = botocore.session.get_session()
    role_arn = 'arn:aws:iam::111122223333:role/lambda-web-test'
    args = SimpleNamespace(
        name='my-fn',
        revision_description=None,
        kms_key_arn=None,
        runtime=None,
        timeout_seconds=None,
        max_concurrency_per_environment=None,
        application_log_level=None,
        system_log_level=None,
    )
    norm = SimpleNamespace(env={}, unset_env=[])
    existing = {
        'buildConfig': {
            'codeConfig': {
                's3Object': {
                    'bucket': 'amzn-s3-demo-bucket',
                    'key': 'old.zip',
                }
            },
            'runtimeConfig': {'runtime': constants.DEFAULT_RUNTIME},
        },
        'serviceConfig': {'executionRoleArn': role_arn},
    }

    request = requests.build_revision_request(
        session,
        args,
        norm,
        role_arn,
        {
            'bucket': 'amzn-s3-demo-bucket',
            'key': 'new.zip',
            'versionId': '',
        },
        existing,
    )
    assert 'versionId' not in request['buildConfig']['codeConfig']['s3Object']
    validate_parameters(
        request,
        _input_shape(session, 'CreateWebFunctionRevision'),
    )


def test_create_endpoint_request_matches_current_input_model():
    session = botocore.session.get_session()
    request = requests.build_create_endpoint_request(
        _endpoint_args(),
        SimpleNamespace(regions=[]),
        'us-east-1',
        'rev-001',
    )

    validate_parameters(
        request,
        _input_shape(session, 'CreateWebFunctionEndpoint'),
    )


def test_update_endpoint_request_matches_current_input_model():
    session = botocore.session.get_session()
    request, note = requests.build_update_endpoint_request(
        _endpoint_args(),
        {
            'endpointName': constants.DEFAULT_ENDPOINT_NAME,
            'authType': constants.DEFAULT_AUTH_TYPE,
            'autoDeploymentMode': constants.DEFAULT_AUTO_DEPLOYMENT_MODE,
            'description': 'existing',
            'scalingConfig': {'maxEnvironments': 3},
            'throttleConfig': {'rateLimit': 1},
        },
        'rev-001',
    )

    assert note is None
    validate_parameters(
        request,
        _input_shape(session, 'UpdateWebFunctionEndpoint'),
    )
