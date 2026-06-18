# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import importlib
import os
import sys
from unittest import mock

import pytest

from botocore.plugin import (
    PluginContext,
    reset_plugin_context,
    set_plugin_context,
)
from botocore.session import get_session
from tests import ClientHTTPStubber


@pytest.fixture(scope="module", autouse=True)
def sys_mock():
    _preserved_sys_path = sys.path[:]
    plugins_dir = os.path.join(os.path.dirname(__file__), "plugins")
    sys.path.append(plugins_dir)
    try:
        yield
    finally:
        sys.path = _preserved_sys_path


def mock_env_for_plugins(plugins_value):
    return mock.patch.dict(
        os.environ,
        {
            'AWS_ACCESS_KEY_ID': 'access_key',
            "AWS_SECRET_ACCESS_KEY": "secret_key",
            'BOTOCORE_EXPERIMENTAL__PLUGINS': plugins_value,
        },
    )


def test_environment_variable():
    plugin_module = importlib.import_module("simple_plugin_test_module")
    test_plugin = plugin_module.plugin_instance
    with mock_env_for_plugins('plugin_name=simple_plugin_test_module'):
        session = get_session()
        client = session.create_client('dynamodb', region_name='us-east-1')
        with ClientHTTPStubber(client) as http_stubber:
            http_stubber.add_response(status=200, body=b'')
            client.list_tables()
        assert len(test_plugin.events_seen) == 1
        assert isinstance(test_plugin.events_seen[0], dict)


def test_recursive_plugin_module():
    plugin_module = importlib.import_module("recursive_plugin_test_module")
    recursive_plugin = plugin_module.plugin_instance
    with mock_env_for_plugins('recursive=recursive_plugin_test_module'):
        session = get_session()
        session.set_credentials('key', 'secret')
        client = session.create_client('dynamodb', region_name='us-east-1')
        with ClientHTTPStubber(client) as http_stubber:
            http_stubber.add_response(status=200, body=b'')
            client.list_tables()
    assert recursive_plugin.called


def test_plugin_not_loaded_when_disabled():
    plugin_mod = importlib.import_module("disabled_test_plugin")
    disabled_plugin = plugin_mod.plugin_instance
    with mock_env_for_plugins('disabled_plugin=disabled_test_plugin'):
        ctx = PluginContext(plugins="DISABLED")
        token = set_plugin_context(ctx)
        try:
            session = get_session()
            session.set_credentials('key', 'secret')
            client = session.create_client('dynamodb', region_name='us-east-1')
            with ClientHTTPStubber(client) as http_stubber:
                http_stubber.add_response(status=200, body=b'')
                client.list_tables()
        finally:
            reset_plugin_context(token)
    assert disabled_plugin.invocations == 0


def test_multiple_plugins_and_malformed():
    plugin1_mod = importlib.import_module("first_of_two_plugins")
    plugin2_mod = importlib.import_module("second_of_two_plugins")
    first_plugin = plugin1_mod.plugin_instance
    second_plugin = plugin2_mod.plugin_instance
    with mock_env_for_plugins(
        'plugin1=first_of_two_plugins,plugin2=second_of_two_plugins,malformedplugin'
    ):
        session = get_session()
        session.set_credentials('key', 'secret')
        client = session.create_client('dynamodb', region_name='us-east-1')
        with ClientHTTPStubber(client) as http_stubber:
            http_stubber.add_response(status=200, body=b'')
            client.list_tables()
    assert first_plugin.invocations == 1
    assert second_plugin.invocations == 1
