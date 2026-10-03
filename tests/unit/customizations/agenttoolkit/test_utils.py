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
import os
from argparse import Namespace
from unittest import mock
from unittest.mock import MagicMock

import pytest
from botocore.session import Session

from awscli.customizations.agenttoolkit.utils import (
    AGENT_TOOLKIT_REGION,
    create_client,
)


def _create_client(region):
    session = MagicMock()
    parsed_globals = Namespace(region=region)
    create_client(session, parsed_globals)
    return session.create_client.call_args


def test_defaults_region_when_none_configured():
    args = _create_client(region=None)
    assert args.kwargs['region_name'] == AGENT_TOOLKIT_REGION


def test_honors_explicit_region():
    args = _create_client(region='us-west-2')
    assert args.kwargs.get('region_name') == 'us-west-2'


DEFAULT_ENDPOINT = 'https://agent-toolkit.us-east-1.api.aws'
GLOBAL_ENDPOINT = 'http://global.example'
SERVICE_ENDPOINT = 'http://agent-toolkit.example'
PROFILE_ENDPOINT_CONFIG = f'[default]\nendpoint_url = {GLOBAL_ENDPOINT}\n'
SERVICES_CONFIG = (
    f'[default]\nendpoint_url = {GLOBAL_ENDPOINT}\nservices = local\n'
    '[services local]\n'
    f'agenttoolkit =\n  endpoint_url = {SERVICE_ENDPOINT}\n'
)


@pytest.mark.parametrize(
    'env,config,endpoint_url,expected',
    [
        ({}, '', None, DEFAULT_ENDPOINT),
        ({'AWS_ENDPOINT_URL': GLOBAL_ENDPOINT}, '', None, DEFAULT_ENDPOINT),
        ({}, PROFILE_ENDPOINT_CONFIG, None, DEFAULT_ENDPOINT),
        (
            {
                'AWS_ENDPOINT_URL': GLOBAL_ENDPOINT,
                'AWS_ENDPOINT_URL_AGENTTOOLKIT': SERVICE_ENDPOINT,
            },
            '',
            None,
            SERVICE_ENDPOINT,
        ),
        (
            {'AWS_ENDPOINT_URL': GLOBAL_ENDPOINT},
            SERVICES_CONFIG,
            None,
            SERVICE_ENDPOINT,
        ),
        (
            {
                'AWS_ENDPOINT_URL_AGENTTOOLKIT': SERVICE_ENDPOINT,
                'AWS_IGNORE_CONFIGURED_ENDPOINT_URLS': 'true',
            },
            '',
            None,
            DEFAULT_ENDPOINT,
        ),
        (
            {'AWS_ENDPOINT_URL': GLOBAL_ENDPOINT},
            '',
            'http://explicit.example',
            'http://explicit.example',
        ),
    ],
)
def test_only_service_specific_endpoints_apply(
    tmp_path, env, config, endpoint_url, expected
):
    config_file = tmp_path / 'config'
    config_file.write_text(config)
    env = {
        'AWS_CONFIG_FILE': str(config_file),
        'AWS_SHARED_CREDENTIALS_FILE': str(tmp_path / 'credentials'),
        **env,
    }
    with mock.patch.dict(os.environ, env, clear=True):
        parsed_globals = Namespace(region=None, endpoint_url=endpoint_url)
        client = create_client(Session(), parsed_globals)
    client.meta.events.register('before-send', _stop_before_sending)
    with pytest.raises(_RequestSent) as sent:
        client.list_skills()
    assert sent.value.url.startswith(f'{expected}/')


def test_global_endpoint_still_applies_to_other_clients(tmp_path):
    config_file = tmp_path / 'config'
    config_file.write_text(PROFILE_ENDPOINT_CONFIG)
    env = {
        'AWS_CONFIG_FILE': str(config_file),
        'AWS_SHARED_CREDENTIALS_FILE': str(tmp_path / 'credentials'),
    }
    with mock.patch.dict(os.environ, env, clear=True):
        session = Session()
        create_client(session, Namespace(region=None, endpoint_url=None))
        s3 = session.create_client('s3', region_name='us-east-1')
    assert s3.meta.endpoint_url == GLOBAL_ENDPOINT


class _RequestSent(Exception):
    def __init__(self, url):
        self.url = url


def _stop_before_sending(request, **kwargs):
    raise _RequestSent(request.url)
