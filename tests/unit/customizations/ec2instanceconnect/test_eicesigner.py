# Copyright 2023 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from urllib.parse import urlencode

import mock
import pytest

from botocore.session import Session
from botocore.signers import RequestSigner
from awscli.customizations.ec2instanceconnect.eicesigner import (
    InstanceConnectEndpointRequestSigner,
)


@pytest.fixture
def service_model_mock():
    return mock.Mock()


@pytest.fixture
def session_mock(service_model_mock):
    session_mock = mock.Mock(spec=Session)
    session_mock.get_service_model.return_value = service_model_mock
    return session_mock


@pytest.fixture
def request_signer_mock():
    return mock.Mock(spec=RequestSigner)


@pytest.fixture
def eice_id():
    return "instanceConnectEndpointId"


@pytest.fixture
def remote_port():
    return "1"


@pytest.fixture
def private_ip():
    return "127.0.0.1"


@pytest.fixture
def dns_name():
    return "amazon.com"


@pytest.fixture
def max_tunnel_duration():
    return "1"


class TestInstanceConnectEndpointRequestSigner:

    def test_get_presigned_url_without_max_tunnel_duration(
            self, session_mock, request_signer_mock, eice_id, remote_port, private_ip, dns_name
    ):
        eice_request_signer = InstanceConnectEndpointRequestSigner(
            session_mock,
            instance_connect_endpoint_dns_name=dns_name,
            instance_connect_endpoint_id=eice_id,
            remote_port=remote_port,
            instance_private_ip=private_ip,
            max_tunnel_duration=None,
            request_singer=request_signer_mock,
        )

        expected_url = "wss://" + dns_name + "/openTunnel?params"
        request_signer_mock.generate_presigned_url.return_value = expected_url

        returned_url = eice_request_signer.get_presigned_url()

        assert returned_url == expected_url

        qs_components = {
            "instanceConnectEndpointId": eice_id,
            "remotePort": remote_port,
            "privateIpAddress": private_ip,
        }
        expected_query_string = urlencode(qs_components)
        expected_request_dict = {
            "url": "wss://"
                   + dns_name
                   + "/openTunnel?"
                   + expected_query_string,
            "body": {},
            "headers": {"host": dns_name},
            "method": "GET",
            "query_string": "",
            "url_path": "/",
            "context": {},
        }
        request_signer_mock.generate_presigned_url.assert_called_with(
            request_dict=expected_request_dict,
            operation_name="openTunnel",
            expires_in=60,
        )

    def test_get_presigned_url_with_max_connection_timeout(
            self, session_mock, request_signer_mock, eice_id, remote_port, private_ip, dns_name, max_tunnel_duration
    ):
        eice_request_signer = InstanceConnectEndpointRequestSigner(
            session_mock,
            instance_connect_endpoint_dns_name=dns_name,
            instance_connect_endpoint_id=eice_id,
            remote_port=remote_port,
            instance_private_ip=private_ip,
            max_tunnel_duration=max_tunnel_duration,
            request_singer=request_signer_mock,
        )

        expected_url = "wss://" + dns_name + "/openTunnel?params"
        request_signer_mock.generate_presigned_url.return_value = expected_url

        returned_url = eice_request_signer.get_presigned_url()

        assert returned_url == expected_url

        qs_components = {
            "instanceConnectEndpointId": eice_id,
            "remotePort": remote_port,
            "privateIpAddress": private_ip,
            "maxTunnelDuration": max_tunnel_duration,
        }
        expected_query_string = urlencode(qs_components)
        expected_request_dict = {
            "url": "wss://"
                   + dns_name
                   + "/openTunnel?"
                   + expected_query_string,
            "body": {},
            "headers": {"host": dns_name},
            "method": "GET",
            "query_string": "",
            "url_path": "/",
            "context": {},
        }
        eice_request_signer._request_signer.generate_presigned_url.assert_called_with(
            request_dict=expected_request_dict,
            operation_name="openTunnel",
            expires_in=60,
        )
