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

from botocore.signers import RequestSigner


class InstanceConnectEndpointRequestSigner:
    def __init__(
            self,
            session,
            instance_connect_endpoint_dns_name,
            instance_connect_endpoint_id,
            remote_port,
            instance_private_ip,
            max_tunnel_duration,
            request_singer=None,
    ):
        service_model = session.get_service_model("ec2-instance-connect")

        if request_singer is None:
            self._request_signer = RequestSigner(
                service_model.service_id,
                session.get_config_variable("region"),
                service_model.signing_name,
                service_model.signature_version,
                session.get_credentials(),
                session.get_component("event_emitter"),
            )
        else:
            self._request_signer = request_singer

        self.instance_connect_endpoint_dns_name = (
            instance_connect_endpoint_dns_name
        )
        self.instance_connect_endpoint_id = instance_connect_endpoint_id
        self.remote_port = remote_port
        self.instance_private_ip = instance_private_ip
        self.max_tunnel_duration = max_tunnel_duration

    def get_presigned_url(self):
        qs_components = {
            "instanceConnectEndpointId": self.instance_connect_endpoint_id,
            "remotePort": self.remote_port,
            "privateIpAddress": self.instance_private_ip,
        }
        if self.max_tunnel_duration:
            qs_components["maxTunnelDuration"] = self.max_tunnel_duration
        query_string = urlencode(qs_components)

        request_dict = {
            "url": f"wss://{self.instance_connect_endpoint_dns_name}/openTunnel?{query_string}",
            "body": {},
            "headers": {"host": self.instance_connect_endpoint_dns_name},
            "method": "GET",
            "query_string": "",
            "url_path": "/",
            "context": {},
        }
        presigned_url = self._request_signer.generate_presigned_url(
            request_dict=request_dict,
            operation_name="openTunnel",
            expires_in=60,
        )
        return presigned_url
