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
import os
import logging
import re
import shutil
import subprocess
import sys
import tempfile

from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ParamValidationError, ConfigurationError
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import PublicFormat, Encoding, PrivateFormat, NoEncryption
from awscli.compat import compat_shell_quote
from awscli.customizations.ec2instanceconnect.eicefetcher import InstanceConnectEndpointRequestFetcher

logger = logging.getLogger(__name__)


class SshCommand(BasicCommand):
    NAME = 'ssh'

    CONNECTION_TYPES = ['auto',
                        'direct',
                        'eice']

    ARG_TABLE = [
        {
            'name': 'instance-id',
            'help_text': 'Specify the ID of the EC2 instance to connect to.',
            'required': True,
        },
        {
            'name': 'instance-ip',
            'help_text': 'Specify the IP address of the instance to connect to.',
            'required': False,
        },
        {
            'name': 'private-key-file',
            'help_text': 'Specify the path to the private key file for login.',
            'required': False,
        },
        {
            'name': 'os-user',
            'help_text': 'Specify the OS SSH user. (Default: ec2-user)',
            'required': False,
            'default': 'ec2-user',
        },
        {
            'name': 'ssh-port',
            'help_text': 'Specify the SSH port. (Default: 22)',
            'required': False,
            'cli_type_name': 'integer',
            'default': '22',
        },
        {
            'name': 'local-forwarding',
            'help_text': 'Specify the local forwarding specification as defined by your OpenSSH client. '
                         '(Example: 3336:remote.host:3306)',
            'required': False,
        },
        {
            'name': 'connection-type',
            'help_text': (
                'Specify how to SSH into the instance. (Default: auto)'
                '<ul>'
                '<li>direct: SSH directly to the instance. '
                'The CLI tries to connect using the IP addresses in the following order: '
                    '<ul>'
                    '<li>Public IPv4</li>'
                    '<li>IPv6</li>'
                    '<li>Private IPv4</li>'
                    '</ul>'
                '</li>'
                '<li>eice: SSH using EC2 Instance Connect Endpoint. The CLI always uses the private IPv4 address.</li>'
                '<li>auto: The CLI automatically determines the connection type (direct or eice) '
                'to use based on the instance info. Currently the CLI tries to connect using the IP addresses '
                'in the following order and with the corresponding connection type:'
                    '<ul>'
                    '<li>Public IPv4: direct</li>'
                    '<li>Private IPv4: eice</li>'
                    '<li>IPv6: direct</li>'
                    '</ul>'
                '</li>'
                '</ul>'
                'In the future, we might change the behavior of the auto connection type. To ensure that your '
                'desired connection type is used, we recommend that you explicitly set the --connection-type '
                'to either direct or eice.'
            ),
            'choices': CONNECTION_TYPES,
            'default': 'auto',
        },
        {
            'name': 'eice-options',
            'help_text': 'Specify the options for your EC2 Instance Connect Endpoint.',
            'schema': {
                'type': 'object',
                'properties': {
                    'maxTunnelDuration': {
                        'type': 'integer',
                        'description': (
                            'Specify the maximum duration (in seconds) for an established TCP connection. '
                            'Default: 3600 seconds (1 hour).'
                        ),
                        'required': False,
                    },
                    'endpointId': {
                        'type': 'string',
                        'description': (
                            'Specify the EC2 Instance Connect Endpoint ID to use to open the tunnel.'
                        ),
                        'required': False,
                    },
                    'dnsName': {
                        'type': 'string',
                        'description': (
                            'Specify the EC2 Instance Connect Endpoint DNS name to use to open '
                            'the tunnel. If this is specified, you must also specify endpointId.'
                        ),
                        'required': False,
                    },
                }
            },
        },
    ]

    DESCRIPTION = 'Connect to your EC2 instance using your OpenSSH client.'

    def __init__(self, session, key_manager=None):
        super(SshCommand, self).__init__(session)
        self._key_manager = KeyManager() if (key_manager is None) else key_manager

    def _run_main(self, parsed_args, parsed_globals):
        self._validate_parsed_args(parsed_args)

        # Describe instance to validate instance exist
        ec2_client = self._session.create_client(
            'ec2',
            region_name=parsed_globals.region,
            verify=parsed_globals.verify_ssl,
            endpoint_url=parsed_globals.endpoint_url,
        )
        instance_metadata = ec2_client.describe_instances(
            InstanceIds=[parsed_args.instance_id]
        )['Reservations'][0]['Instances'][0]

        private_ip_address = instance_metadata.get('PrivateIpAddress')
        public_ip_address = instance_metadata.get('PublicIpAddress')
        ipv6_address = instance_metadata.get('Ipv6Address')

        use_open_tunnel = False
        ip_address_to_connect = None
        if parsed_args.instance_ip:
            use_open_tunnel = parsed_args.connection_type == 'eice'
            ip_address_to_connect = parsed_args.instance_ip
        elif parsed_args.connection_type == 'eice' or parsed_args.eice_options:
            use_open_tunnel = True
            ip_address_to_connect = private_ip_address
        elif parsed_args.connection_type == 'direct':
            use_open_tunnel = False
            ip_address_to_connect = public_ip_address or ipv6_address or private_ip_address
        elif parsed_args.connection_type == 'auto':
            # In case of auto we use IPv4 address first and then IPv6 because right now most instance have these, but
            # in future we might want to switch this logic to where we select IPv6 first and then fallback to IPv4.
            if public_ip_address:
                use_open_tunnel = False
                ip_address_to_connect = public_ip_address
            elif private_ip_address:
                use_open_tunnel = True
                ip_address_to_connect = private_ip_address
            elif ipv6_address:
                use_open_tunnel = False
                ip_address_to_connect = ipv6_address

        if ip_address_to_connect is None:
            raise ParamValidationError('Unable to find any IP address on the instance to connect to.')

        instance_connect_endpoint_id = self._get_eice_option(parsed_args.eice_options, 'endpointId')
        instance_connect_endpoint_dns_name = self._get_eice_option(parsed_args.eice_options, 'dnsName')
        if use_open_tunnel and not instance_connect_endpoint_dns_name:
            eice_fetcher = InstanceConnectEndpointRequestFetcher()
            eice_info = eice_fetcher.get_available_instance_connect_endpoint(
                ec2_client,
                instance_metadata["VpcId"],
                instance_metadata["SubnetId"],
                instance_connect_endpoint_id
            )
            instance_connect_endpoint_id = eice_info["InstanceConnectEndpointId"]

            is_fips_enabled = self._session.get_config_variable('use_fips_endpoint')
            instance_connect_endpoint_dns_name = eice_fetcher.get_eice_dns_name(eice_info, is_fips_enabled)

        # Validate ssh key exist (either use user defined or create new one)
        key_file = parsed_args.private_key_file

        with tempfile.TemporaryDirectory() as tmp_dir:
            if not key_file:
                key_file = os.path.join(tmp_dir, 'private-key')
                logger.debug('Generate new ssh key and upload')
                private_pem_bytes = self._generate_and_upload_ssh_key(
                    parsed_args.instance_id, parsed_args.os_user, parsed_globals)

                with open(key_file, 'wb') as fd:
                    fd.write(private_pem_bytes)
                    logger.debug('Generated temporary key file: %s', key_file)
                os.chmod(key_file, 0o400)

            return self._ssh(
                use_open_tunnel,
                parsed_args.instance_id,
                parsed_args.ssh_port,
                parsed_args.os_user,
                parsed_args.local_forwarding,
                key_file,
                ip_address_to_connect,
                instance_connect_endpoint_id,
                instance_connect_endpoint_dns_name,
                self._get_eice_option(parsed_args.eice_options, 'maxTunnelDuration'),
                parsed_globals
            )

    def _validate_parsed_args(self, parsed_args):
        if parsed_args.instance_id:
            if not re.search("^i-[0-9a-zA-Z]+$", parsed_args.instance_id):
                raise ParamValidationError('The specified instance ID is invalid. '
                                           'Provide the full instance ID in the form i-xxxxxxxxxxxxxxxxx.')

        eice_options = parsed_args.eice_options
        if parsed_args.connection_type == "direct" and eice_options:
            raise ParamValidationError('eice-options can\'t be specified when connection type is direct.')

        if self._get_eice_option(eice_options, 'dnsName') and not self._get_eice_option(eice_options, 'endpointId'):
            raise ParamValidationError('When specifying dnsName, you must specify endpointId.')

        if eice_options and 'maxTunnelDuration' in eice_options:
            max_tunnel_duration = eice_options['maxTunnelDuration']
            if max_tunnel_duration is not None and (max_tunnel_duration < 1 or max_tunnel_duration > 3_600):
                raise ParamValidationError(
                    'Invalid value specified for maxTunnelDuration. Value must be greater than 1 and '
                    'less than 3600.'
                )

        if self._get_eice_option(eice_options, 'endpointId'):
            if not re.search("^eice-[0-9a-zA-Z_]+$", eice_options['endpointId']):
                raise ParamValidationError('The specified endpointId is invalid. '
                                           'Provide the full EC2 Instance Connect Endpoint ID in '
                                           'the form eice-xxxxxxxxxxxxxxxxx.')

        if self._get_eice_option(eice_options, 'dnsName'):
            if not re.search('^[0-9a-zA-Z.-]+$', eice_options['dnsName']):
                raise ParamValidationError('The specified dnsName is invalid.')

        if parsed_args.instance_ip and parsed_args.connection_type == 'auto':
            raise ParamValidationError('When specifying instance-ip, you must specify connection-type.')

    def _get_eice_option(self, eice_options, option):
        if eice_options:
            return eice_options.get(option)
        return None

    def _generate_and_upload_ssh_key(self, instance_id, os_user, parsed_globals):
        private_key = self._key_manager.generate_key()

        logger.debug('Upload public ssh key to instance')
        ec2_instance_connect_client = self._session.create_client(
            'ec2-instance-connect',
            region_name=parsed_globals.region,
            verify=parsed_globals.verify_ssl,
        )
        public_key = self._key_manager.get_public_key(private_key)
        self._key_manager.upload_public_key(ec2_instance_connect_client, instance_id, os_user, public_key)

        return self._key_manager.get_private_pem(private_key)

    def _generate_open_tunnel_command(self, instance_id, private_ip_address, ssh_port, eice_id, eice_dns_name,
                                      max_tunnel_duration, parsed_globals):
        aws_cli_path = sys.argv[0]
        proxy_command = [
            aws_cli_path, 'ec2-instance-connect', 'open-tunnel',
            '--instance-id', instance_id,
            '--private-ip-address', private_ip_address,
            '--remote-port', str(ssh_port),
        ]
        logger.debug(f"Using aws: {aws_cli_path}")

        if parsed_globals.region:
            proxy_command.append('--region')
            proxy_command.append(parsed_globals.region)
        if parsed_globals.profile:
            proxy_command.append('--profile')
            proxy_command.append(parsed_globals.profile)
        if eice_id:
            proxy_command.append('--instance-connect-endpoint-id')
            proxy_command.append(eice_id)
        if eice_dns_name:
            proxy_command.append('--instance-connect-endpoint-dns-name')
            proxy_command.append(eice_dns_name)
        if max_tunnel_duration:
            proxy_command.append('--max-tunnel-duration')
            proxy_command.append(str(max_tunnel_duration))

        return proxy_command

    def _ssh(self, use_open_tunnel, instance_id, ssh_port, os_user, local_forwarding, key_file,
             ip_address, eice_id, eice_dns_name, max_tunnel_duration, parsed_globals):

        proxy_command = self._generate_open_tunnel_command(
            instance_id, ip_address, ssh_port, eice_id, eice_dns_name, max_tunnel_duration, parsed_globals)

        command = [
            'ssh',
            # adding ServerAliveInterval as default because it offers better customer experience as it let customer
            # know about terminated connections. If we want to allow customer to override this we can add additional
            # parameter to this cli command
            '-o', 'ServerAliveInterval=5',
            '-p', str(ssh_port),
            '-i', key_file, os_user + '@' + ip_address,
        ]

        ssh_path = shutil.which('ssh')
        if ssh_path:
            command[0] = ssh_path
            logger.debug(f"Using ssh: {ssh_path}")
        else:
            raise ConfigurationError('SSH not available. Please refer to the documentation '
                                     'at https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Connect-using-EC2-Instance-Connect-Endpoint.html.')

        # Add local-forwarding option if users passed local-forwarding
        if local_forwarding:
            command.insert(-1, '-L')
            command.insert(-1, local_forwarding)

        # If --debug is define lets add '-v' to ssh to generate debug level logs
        if parsed_globals.debug:
            command.insert(-1, '-v')

        # If we are trying to connect to instance in private subnet lets use open-tunnel command to use eice
        if use_open_tunnel:
            command.insert(-1, '-o')
            command.insert(-1, f"ProxyCommand={' '.join(compat_shell_quote(a) for a in proxy_command)}")

        logger.debug('Invoking SSH command: %s', command)
        rc = subprocess.call(command)
        return rc


class KeyManager:
    def generate_key(self):
        logger.debug('Generate Ed25519 Key')
        return Ed25519PrivateKey.generate()

    def get_public_key(self, private_key):
        return private_key.public_key().public_bytes(
            encoding=Encoding.OpenSSH,
            format=PublicFormat.OpenSSH
        )

    def get_private_pem(self, private_key):
        return private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.OpenSSH,
            encryption_algorithm=NoEncryption()
        )

    def upload_public_key(self, ec2_instance_connect_client, instance_id, os_user, public_key):
        logger.debug('Upload ssh key to instance')
        ec2_instance_connect_client.send_ssh_public_key(
            InstanceId=instance_id,
            InstanceOSUser=os_user,
            SSHPublicKey=public_key.decode(),
        )
