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
import logging
import sys

from awscli.customizations.commands import BasicCommand
from awscli.customizations.ec2instanceconnect.eicesigner import (
    InstanceConnectEndpointRequestSigner,
)
from awscli.customizations.ec2instanceconnect.websocket import WebsocketManager
from awscli.customizations.exceptions import ParamValidationError
from awscli.customizations.ec2instanceconnect.eicefetcher import InstanceConnectEndpointRequestFetcher

logger = logging.getLogger(__name__)


class OpenTunnelCommand(BasicCommand):
    NAME = "open-tunnel"

    DESCRIPTION = "Opens a websocket tunnel to the specified EC2 Instance or private ip."

    ARG_TABLE = [
        {
            "name": "instance-id",
            "help_text": "Specify the id of the EC2 instance that a tunnel should be opened for.",
            "required": False,
        },
        {
            "name": "instance-connect-endpoint-id",
            "help_text": "Specify the EC2 Instance Connect Endpoint Id that should be used to open the tunnel.",
            "required": False,
        },
        {
            "name": "instance-connect-endpoint-dns-name",
            "help_text": (
                "Specify the EC2 Instance Connect Endpoint DNS Name that should be used to open the tunnel. "
                "If this is specified, you must specify instance-connect-endpoint-id."
            ),
            "required": False,
        },
        {
            "name": "private-ip-address",
            "help_text": (
                "Specify the private ip address to open a tunnel for. "
                "If this is specified, you must specify instance-connect-endpoint-id."
            ),
            "required": False,
        },
        {
            "name": "remote-port",
            "help_text": "Specify the remote port to connect to on the instance. This defaults to port 22.",
            "default": 22,
            "cli_type_name": "integer",
            "required": False,
        },
        {
            "name": "local-port",
            "help_text": (
                "Specify the local port to listen on. Each new connection will have a separate websocket "
                "tunnel read and write to it."
            ),
            "cli_type_name": "integer",
            "required": False,
        },
        {
            "name": "local-ip",
            "help_text": "Specify the local IP address to listen on. This defaults to localhost.",
            "default": "localhost",
            "required": False,
        },
        {
            "name": "max-tunnel-duration",
            "help_text": (
                "Specify the maximum time, in seconds, to keep a websocket tunnel alive for. This "
                "defaults to 3600 seconds."
            ),
            "cli_type_name": "integer",
            "required": False,
        },
        {
            "name": "max-websocket-connections",
            "help_text": (
                "Specify the maximum amount of websocket connections allowed when local-port is specified. This value "
                "defaults to 10. "
            ),
            "default": 10,
            "cli_type_name": "integer",
            "required": False,
        },
    ]

    def _run_main(self, parsed_args, parsed_globals):
        self._validate_parsed_args(parsed_args)
        ec2_client = self._session.create_client(
            "ec2",
            region_name=parsed_globals.region,
            verify=parsed_globals.verify_ssl,
        )

        instance_vpc_id = None
        instance_subnet_id = None
        private_ip_address = parsed_args.private_ip_address
        if not private_ip_address:
            instance_metadata = ec2_client.describe_instances(
                InstanceIds=[parsed_args.instance_id]
            )["Reservations"][0]["Instances"][0]
            instance_vpc_id = instance_metadata["VpcId"]
            instance_subnet_id = instance_metadata["SubnetId"]
            private_ip_address = instance_metadata["PrivateIpAddress"]

        instance_connect_endpoint_id = parsed_args.instance_connect_endpoint_id
        instance_connect_endpoint_dns_name = (
            parsed_args.instance_connect_endpoint_dns_name
        )
        if not instance_connect_endpoint_dns_name:
            eice_fetcher = InstanceConnectEndpointRequestFetcher()
            eice = eice_fetcher.get_available_instance_connect_endpoint(
                ec2_client,
                instance_vpc_id,
                instance_subnet_id,
                parsed_args.instance_connect_endpoint_id,
            )
            instance_connect_endpoint_id = eice["InstanceConnectEndpointId"]

            is_fips_enabled = self._session.get_config_variable('use_fips_endpoint')
            instance_connect_endpoint_dns_name = eice_fetcher.get_eice_dns_name(eice, is_fips_enabled)

        logger.debug(f"Using endpoint dns: {instance_connect_endpoint_dns_name}")
        eice_request_signer = InstanceConnectEndpointRequestSigner(
            self._session,
            instance_connect_endpoint_dns_name=instance_connect_endpoint_dns_name,
            instance_connect_endpoint_id=instance_connect_endpoint_id,
            remote_port=parsed_args.remote_port,
            instance_private_ip=private_ip_address,
            max_tunnel_duration=parsed_args.max_tunnel_duration,
        )

        with WebsocketManager(
                parsed_args.local_port, parsed_args.local_ip, parsed_args.max_websocket_connections, eice_request_signer, self._session.user_agent(),
        ) as websocket_manager:
            websocket_manager.run()
        return 0

    def _validate_parsed_args(self, parsed_args):
        if not parsed_args.instance_id and not parsed_args.private_ip_address:
            raise ParamValidationError("Specify an instance id or private ip.")
        if parsed_args.instance_connect_endpoint_dns_name and not parsed_args.instance_connect_endpoint_id:
            raise ParamValidationError("Specify an instance connect endpoint id when providing a DNS name.")
        if parsed_args.private_ip_address and not parsed_args.instance_connect_endpoint_id:
            raise ParamValidationError("Specify an instance connect endpoint id when providing a private ip.")
        if parsed_args.max_tunnel_duration is not None and (
                parsed_args.max_tunnel_duration < 1
                or parsed_args.max_tunnel_duration > 3_600
        ):
            raise ParamValidationError(
                "Invalid max connection timeout specified. Value must be greater than 1 and "
                "less than 3600."
            )
        if parsed_args.local_port is None and sys.stdin.isatty():
            raise ParamValidationError(
                "This command does not support interactive mode. You must use this command as a proxy or in listener "
                "mode. "
            )