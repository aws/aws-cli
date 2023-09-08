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
from unittest import mock

import os
import pytest
import sys

from tests import SessionStubber, AWSRequest, CLIRunner, HTTPResponse


@pytest.fixture
def session_stubber():
    return SessionStubber()


@pytest.fixture
def region():
    return "us-west-2"


@pytest.fixture
def aws_config_file(tmp_path):
    config_file = os.path.join(tmp_path, 'aws-config-file-for-ssh-command')
    with open(config_file, 'wb') as fd:
        fd.write(
            b'[profile test-profile]\n'
            b'aws_access_key_id=access_key\n'
            b'aws_secret_access_key=secret_key\n'
            b'[profile test-fips]\n'
            b'use_fips_endpoint=true\n'
            b'aws_access_key_id=access_key\n'
            b'aws_secret_access_key=secret_key\n')
        return config_file


@pytest.fixture
def cli_runner(session_stubber, region, aws_config_file):
    cli_runner = CLIRunner(session_stubber=session_stubber)
    cli_runner.env["AWS_DEFAULT_REGION"] = region
    cli_runner.env["AWS_CONFIG_FILE"] = aws_config_file
    return cli_runner


def get_describe_private_instance_response():
    return """
     <DescribeInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
         <reservationSet>
             <item>
                 <instancesSet>
                     <item>
                         <instanceId>i-123</instanceId>
                         <subnetId>subnet-123</subnetId>
                         <vpcId>vpc-123</vpcId>
                         <privateIpAddress>10.0.0.0</privateIpAddress>
                     </item>
                 </instancesSet>
             </item>
         </reservationSet>
     </DescribeInstancesResponse>
     """


@pytest.fixture
def describe_private_instance_response():
    return get_describe_private_instance_response()


def get_describe_public_instance_response():
    return """
     <DescribeInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
         <reservationSet>
             <item>
                 <instancesSet>
                     <item>
                         <instanceId>i-123</instanceId>
                         <subnetId>subnet-123</subnetId>
                         <vpcId>vpc-123</vpcId>
                         <ipAddress>11.11.11.11</ipAddress>
                         <privateIpAddress>10.0.0.0</privateIpAddress>
                         <ipv6Addresses>2600:1f10:4f8e:db01:73f5:6b9d:c0da:1c27</ipv6Addresses>
                     </item>
                 </instancesSet>
             </item>
         </reservationSet>
     </DescribeInstancesResponse>
     """


@pytest.fixture
def describe_public_instance_response():
    return get_describe_public_instance_response()


def get_describe_ipv6_instance_response():
    return """
     <DescribeInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
         <reservationSet>
             <item>
                 <instancesSet>
                     <item>
                         <instanceId>i-123</instanceId>
                         <subnetId>subnet-123</subnetId>
                         <vpcId>vpc-123</vpcId>
                         <privateIpAddress>10.0.0.0</privateIpAddress>
                         <ipv6Address>2600:1f10:4f8e:db01:73f5:6b9d:c0da:1c27</ipv6Address>
                     </item>
                 </instancesSet>
             </item>
         </reservationSet>
     </DescribeInstancesResponse>
     """


@pytest.fixture
def describe_ipv6_instance_response():
    return get_describe_ipv6_instance_response()


@pytest.fixture
def describe_no_ip_instance_response():
    return """
     <DescribeInstancesResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
         <reservationSet>
             <item>
                 <instancesSet>
                     <item>
                         <instanceId>i-123</instanceId>
                         <subnetId>subnet-123</subnetId>
                         <vpcId>vpc-123</vpcId>
                     </item>
                 </instancesSet>
             </item>
         </reservationSet>
     </DescribeInstancesResponse>
     """


@pytest.fixture
def send_ssh_public_key_response():
    return b'{"RequestId":"01adeb55-3f80-4736-b789-d57feb69691d","Success":true}'


@pytest.fixture
def request_params_for_describe_instance():
    return {'InstanceIds': ['i-123']}


def get_describe_eice_response():
    return f"""
    <DescribeInstanceConnectEndpointsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
        <instanceConnectEndpointSet>
            <item>
                <dnsName>dns.com</dnsName>
                <fipsDnsName>fips.dns.com</fipsDnsName>
                <instanceConnectEndpointId>eice-123</instanceConnectEndpointId>
                <state>create-complete</state>
                <subnetId>subnet-123</subnetId>
                <vpcId>vpc-123</vpcId>
            </item>
        </instanceConnectEndpointSet>
    </DescribeInstanceConnectEndpointsResponse>
    """


@pytest.fixture
def describe_eice_response():
    return get_describe_eice_response()


def get_request_params_for_describe_eice():
    return {'Filters': [{'Name': 'state', 'Values': ['create-complete']}, {'Name': 'vpc-id', 'Values': ['vpc-123']}]}


def get_request_params_for_describe_eice_with_eice_id():
    return {'Filters': [{'Name': 'state', 'Values': ['create-complete']}], 'InstanceConnectEndpointIds': ['eice-12345']}


class TestSSHCommand:
    @pytest.mark.parametrize(
        "describe_instance_response,describe_eice_response,request_params_for_describe_eice,cli_input,expected_ssh_command",
        [
            pytest.param(
                get_describe_private_instance_response(),
                get_describe_eice_response(),
                get_request_params_for_describe_eice(),
                [
                    "ec2-instance-connect", "ssh",
                    "--instance-id", "i-123",
                    "--private-key-file", "/tmp/ssh-file",
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '22', '-i', '/tmp/ssh-file',
                    '-o', 'ProxyCommand=aws ec2-instance-connect open-tunnel --instance-id i-123 '
                          '--private-ip-address 10.0.0.0 --remote-port 22 '
                          '--instance-connect-endpoint-id eice-123 --instance-connect-endpoint-dns-name dns.com',
                    'ec2-user@10.0.0.0'
                ],
                id='Open-Tunnel: connect by instance id + key'
            ),

            pytest.param(
                get_describe_private_instance_response(),
                get_describe_eice_response(),
                get_request_params_for_describe_eice_with_eice_id(),
                [
                    "ec2-instance-connect", "ssh",
                    "--private-key-file", "/tmp/ssh-file",
                    "--instance-id", "i-123",
                    "--eice-options", "endpointId=eice-12345",
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '22', '-i', '/tmp/ssh-file',
                    '-o',
                    'ProxyCommand=aws ec2-instance-connect open-tunnel --instance-id i-123 '
                    '--private-ip-address 10.0.0.0 --remote-port 22 '
                    '--instance-connect-endpoint-id eice-123 --instance-connect-endpoint-dns-name dns.com',
                    'ec2-user@10.0.0.0'
                ],
                id='Open-Tunnel: connect to specific EICE'
            ),

            pytest.param(
                get_describe_private_instance_response(),
                None,
                None,
                [
                    "ec2-instance-connect", "ssh",
                    "--private-key-file", "/tmp/ssh-file",
                    "--instance-id", "i-123",
                    "--eice-options", "endpointId=eice-12345,dnsName=dns.domain.com",
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '22', '-i', '/tmp/ssh-file',
                    '-o',
                    'ProxyCommand=aws ec2-instance-connect open-tunnel --instance-id i-123 '
                    '--private-ip-address 10.0.0.0 --remote-port 22 '
                    '--instance-connect-endpoint-id eice-12345 --instance-connect-endpoint-dns-name dns.domain.com',
                    'ec2-user@10.0.0.0'
                ],
                id="Open-Tunnel: connect by eice id + domain"
            ),

            pytest.param(
                get_describe_private_instance_response(),
                get_describe_eice_response(),
                get_request_params_for_describe_eice(),
                [
                    "ec2-instance-connect", "ssh",
                    "--private-key-file", "/tmp/ssh-file",
                    "--instance-id", "i-123",
                    "--eice-options", "maxTunnelDuration=61",
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '22', '-i', '/tmp/ssh-file',
                    '-o',
                    'ProxyCommand=aws ec2-instance-connect open-tunnel --instance-id i-123 '
                    '--private-ip-address 10.0.0.0 --remote-port 22 '
                    '--instance-connect-endpoint-id eice-123 --instance-connect-endpoint-dns-name dns.com '
                    '--max-tunnel-duration 61',
                    'ec2-user@10.0.0.0'
                ],
                id="Open-Tunnel: allow customer to define maxTunnelDuration"
            ),

            pytest.param(
                get_describe_private_instance_response(),
                get_describe_eice_response(),
                get_request_params_for_describe_eice(),
                [
                    "ec2-instance-connect", "ssh",
                    "--private-key-file", "/tmp/ssh-file",
                    "--instance-id", "i-123",
                    "--ssh-port", "24",
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '24', '-i', '/tmp/ssh-file',
                    '-o',
                    'ProxyCommand=aws ec2-instance-connect open-tunnel --instance-id i-123 '
                    '--private-ip-address 10.0.0.0 --remote-port 24 '
                    '--instance-connect-endpoint-id eice-123 --instance-connect-endpoint-dns-name dns.com',
                    'ec2-user@10.0.0.0'
                ],
                id="Open-Tunnel: allow customer to define ssh port"
            ),

            pytest.param(
                get_describe_private_instance_response(),
                get_describe_eice_response(),
                get_request_params_for_describe_eice(),
                [
                    "ec2-instance-connect", "ssh",
                    "--private-key-file", "/tmp/ssh-file",
                    "--instance-id", "i-123",
                    "--os-user", "new-user",
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '22', '-i', '/tmp/ssh-file',
                    '-o',
                    'ProxyCommand=aws ec2-instance-connect open-tunnel --instance-id i-123 '
                    '--private-ip-address 10.0.0.0 --remote-port 22 '
                    '--instance-connect-endpoint-id eice-123 --instance-connect-endpoint-dns-name dns.com',
                    'new-user@10.0.0.0'
                ],
                id='Open-Tunnel: allow customer to define ssh user'
            ),

            pytest.param(
                get_describe_private_instance_response(),
                get_describe_eice_response(),
                get_request_params_for_describe_eice(),
                [
                    "ec2-instance-connect", "ssh",
                    "--private-key-file", "/tmp/ssh-file",
                    "--instance-id", "i-123",
                    "--local-forwarding", "8080:localhost:9090",
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '22', '-i', '/tmp/ssh-file',
                    '-L', '8080:localhost:9090',
                    '-o',
                    'ProxyCommand=aws ec2-instance-connect open-tunnel --instance-id i-123 '
                    '--private-ip-address 10.0.0.0 --remote-port 22 '
                    '--instance-connect-endpoint-id eice-123 --instance-connect-endpoint-dns-name dns.com',
                    'ec2-user@10.0.0.0'
                ],
                id='Open-Tunnel: allow customer to local-forwarding'
            ),

            pytest.param(
                get_describe_private_instance_response(),
                get_describe_eice_response(),
                get_request_params_for_describe_eice(),
                [
                    "ec2-instance-connect", "ssh",
                    "--instance-id", "i-123",
                    "--private-key-file", "/tmp/ssh-file",
                    "--region", "us-east-2",
                    "--profile", "test-profile"
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '22', '-i', '/tmp/ssh-file',
                    '-o',
                    'ProxyCommand=aws ec2-instance-connect open-tunnel --instance-id i-123 '
                    '--private-ip-address 10.0.0.0 --remote-port 22 --region us-east-2 --profile test-profile '
                    '--instance-connect-endpoint-id eice-123 --instance-connect-endpoint-dns-name dns.com',
                    'ec2-user@10.0.0.0'
                ],
                id='Open-Tunnel: pass global parameters to sub-command'
            ),

            pytest.param(
                get_describe_public_instance_response(),
                get_describe_eice_response(),
                get_request_params_for_describe_eice(),
                [
                    "ec2-instance-connect", "ssh",
                    "--instance-id", "i-123",
                    "--private-key-file", "/tmp/ssh-file",
                    "--connection-type", "eice"
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '22', '-i', '/tmp/ssh-file',
                    '-o',
                    'ProxyCommand=aws ec2-instance-connect open-tunnel --instance-id i-123 '
                    '--private-ip-address 10.0.0.0 --remote-port 22 '
                    '--instance-connect-endpoint-id eice-123 --instance-connect-endpoint-dns-name dns.com',
                    'ec2-user@10.0.0.0'
                ],
                id='Open-Tunnel: select private IP when connection type eice'
            ),

            pytest.param(
                get_describe_private_instance_response(),
                get_describe_eice_response(),
                get_request_params_for_describe_eice(),
                [
                    "ec2-instance-connect", "ssh",
                    "--instance-id", "i-123",
                    "--private-key-file", "/tmp/ssh-file",
                    "--profile", "test-fips",
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '22', '-i', '/tmp/ssh-file',
                    '-o', 'ProxyCommand=aws ec2-instance-connect open-tunnel --instance-id i-123 '
                          '--private-ip-address 10.0.0.0 --remote-port 22 --profile test-fips '
                          '--instance-connect-endpoint-id eice-123 '
                          '--instance-connect-endpoint-dns-name fips.dns.com',
                    'ec2-user@10.0.0.0'
                ],
                id='Open-Tunnel: connect by instance id + key to fips endpoint'
            ),

            pytest.param(
                get_describe_public_instance_response(),
                get_describe_eice_response(),
                get_request_params_for_describe_eice(),
                [
                    "ec2-instance-connect", "ssh",
                    "--instance-id", "i-123",
                    "--private-key-file", "/tmp/ssh-file",
                    "--eice-options", "maxTunnelDuration=61",
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '22', '-i', '/tmp/ssh-file',
                    '-o', 'ProxyCommand=aws ec2-instance-connect open-tunnel --instance-id i-123 '
                          '--private-ip-address 10.0.0.0 --remote-port 22 '
                          '--instance-connect-endpoint-id eice-123 --instance-connect-endpoint-dns-name dns.com '
                          '--max-tunnel-duration 61',
                    'ec2-user@10.0.0.0'
                ],
                id='Open-Tunnel: use private ip and eice when eice options defined without connection-type'
            ),

            pytest.param(
                get_describe_public_instance_response(),
                get_describe_eice_response(),
                get_request_params_for_describe_eice(),
                [
                    "ec2-instance-connect", "ssh",
                    "--instance-id", "i-123",
                    "--private-key-file", "/tmp/ssh-file",
                    "--connection-type", "eice",
                    "--instance-ip", "1.10.10.10",
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '22', '-i', '/tmp/ssh-file',
                    '-o', 'ProxyCommand=aws ec2-instance-connect open-tunnel --instance-id i-123 '
                          '--private-ip-address 1.10.10.10 --remote-port 22 '
                          '--instance-connect-endpoint-id eice-123 --instance-connect-endpoint-dns-name dns.com',
                    'ec2-user@1.10.10.10'
                ],
                id='Open-Tunnel: use provided ip'
            ),

            pytest.param(
                get_describe_public_instance_response(),
                None,
                None,
                [
                    "ec2-instance-connect", "ssh",
                    "--instance-id", "i-123",
                    "--private-key-file", "/tmp/ssh-file",
                    "--ssh-port", "24",
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '24', '-i', '/tmp/ssh-file',
                    'ec2-user@11.11.11.11'
                ],
                id='Public: connect to public IP'
            ),

            pytest.param(
                get_describe_public_instance_response(),
                None,
                None,
                [
                    "ec2-instance-connect", "ssh",
                    "--instance-id", "i-123",
                    "--private-key-file", "/tmp/ssh-file",
                    "--instance-ip", "10.0.0.1",
                    "--connection-type", "direct",
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '22', '-i', '/tmp/ssh-file',
                    'ec2-user@10.0.0.1'
                ],
                id='Public: connect to provided ip address'
            ),

            pytest.param(
                get_describe_public_instance_response(),
                None,
                None,
                [
                    "ec2-instance-connect", "ssh",
                    "--instance-id", "i-123",
                    "--private-key-file", "/tmp/ssh-file",
                    "--connection-type", "direct",
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '22', '-i', '/tmp/ssh-file',
                    'ec2-user@11.11.11.11'
                ],
                id='Public: use public when connection-type direct'
            ),

            pytest.param(
                get_describe_private_instance_response(),
                None,
                None,
                [
                    "ec2-instance-connect", "ssh",
                    "--instance-id", "i-123",
                    "--private-key-file", "/tmp/ssh-file",
                    "--connection-type", "direct",
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '22', '-i', '/tmp/ssh-file',
                    'ec2-user@10.0.0.0'
                ],
                id='Public: use private ip since no public ip when connection-type direct'
            ),

            pytest.param(
                get_describe_ipv6_instance_response(),
                None,
                None,
                [
                    "ec2-instance-connect", "ssh",
                    "--instance-id", "i-123",
                    "--private-key-file", "/tmp/ssh-file",
                    "--connection-type", "direct"
                ],
                [
                    'ssh', '-o', 'ServerAliveInterval=5',
                    '-p', '22', '-i', '/tmp/ssh-file',
                    'ec2-user@2600:1f10:4f8e:db01:73f5:6b9d:c0da:1c27'
                ],
                id='Public: IPv6: use ipv6 when connection-type direct and no IPv4 address'
            ),
        ])
    @mock.patch("shutil.which")
    @mock.patch("subprocess.call")
    @mock.patch.object(sys, 'argv', ['aws'])
    def test_successful_ssh_for_instance(self, mock_subproc_call, mock_which, cli_runner,
                                         request_params_for_describe_instance,
                                         describe_instance_response, describe_eice_response,
                                         request_params_for_describe_eice, cli_input, expected_ssh_command):
        mock_which.return_value = "ssh"
        mock_subproc_call.return_value = 0
        cli_runner.add_response(HTTPResponse(body=describe_instance_response))
        if describe_eice_response:
            cli_runner.add_response(HTTPResponse(body=describe_eice_response))

        result = cli_runner.run(cli_input)

        assert 0 == result.rc
        assert mock_subproc_call.called
        requests = [
            AWSRequest(
                service_name='ec2',
                operation_name='DescribeInstances',
                params=request_params_for_describe_instance,
            ),
        ]
        if describe_eice_response:
            requests += [
                AWSRequest(
                    service_name='ec2',
                    operation_name='DescribeInstanceConnectEndpoints',
                    params=request_params_for_describe_eice,
                ),
            ]
        assert result.aws_requests == requests
        mock_which.assert_called_once_with('ssh')
        mock_subproc_call.assert_called_once_with(expected_ssh_command)

    @mock.patch("shutil.which")
    @mock.patch("subprocess.call")
    @mock.patch.object(sys, 'argv', ['aws.cmd'])
    def test_valid_input_without_ssh_key(self, mock_subproc_call, mock_which, cli_runner, describe_eice_response,
                                         describe_private_instance_response, send_ssh_public_key_response):
        mock_which.return_value = '/some/path/to/ssh'
        mock_subproc_call.return_value = 0
        cli_runner.add_response(HTTPResponse(body=describe_private_instance_response))
        cli_runner.add_response(HTTPResponse(body=describe_eice_response))
        cli_runner.add_response(HTTPResponse(body=send_ssh_public_key_response))

        result = cli_runner.run([
            "ec2-instance-connect", "ssh",
            "--instance-id", "i-04997c129f59becde",
        ])

        assert 0 == result.rc
        assert mock_subproc_call.called
        assert result.aws_requests == [
            AWSRequest(
                service_name='ec2',
                operation_name='DescribeInstances',
                params={'InstanceIds': ['i-04997c129f59becde']},
            ),
            AWSRequest(
                service_name='ec2',
                operation_name='DescribeInstanceConnectEndpoints',
                params=mock.ANY,
            ),
            AWSRequest(
                service_name='ec2-instance-connect',
                operation_name='SendSSHPublicKey',
                params=mock.ANY,
            ),
        ]
        mock_which.assert_called_once_with('ssh')
        mock_subproc_call.assert_called_once_with([
            '/some/path/to/ssh', '-o', 'ServerAliveInterval=5',
            '-p', '22', '-i', mock.ANY,
            '-o',
            'ProxyCommand=aws.cmd ec2-instance-connect open-tunnel --instance-id i-04997c129f59becde '
            '--private-ip-address 10.0.0.0 --remote-port 22 '
            '--instance-connect-endpoint-id eice-123 --instance-connect-endpoint-dns-name dns.com',
            'ec2-user@10.0.0.0'
        ])

    def test_no_ip_on_instance(self, cli_runner, describe_no_ip_instance_response):
        cli_runner.add_response(HTTPResponse(body=describe_no_ip_instance_response))

        result = cli_runner.run([
            "ec2-instance-connect", "ssh",
            "--instance-id", "i-04997c129f59becde",
            "--private-key-file", "/tmp/ssh-file",
        ])

        assert 252 == result.rc
        assert 'Unable to find any IP address on the instance to connect to.' in result.stderr

    def test_command_fails_when_eice_connection_type_and_no_private_ip(
            self, cli_runner, describe_no_ip_instance_response):
        cli_runner.add_response(HTTPResponse(body=describe_no_ip_instance_response))

        result = cli_runner.run([
            "ec2-instance-connect", "ssh",
            "--instance-id", "i-04997c129f59becde",
            "--private-key-file", "/tmp/ssh-file",
            "--connection-type", "eice"
        ])

        assert 252 == result.rc
        assert 'Unable to find any IP address on the instance to connect to.' in result.stderr

    @pytest.mark.parametrize("cli_input,expected_error_code,expected", [
        pytest.param(
            [
                "ec2-instance-connect", "ssh",
            ],
            252,
            "the following arguments are required: --instance-id",
            id="Failure: Customer must provide instance-id"
        ),

        pytest.param(
            [
                "ec2-instance-connect", "ssh",
                "--instance-id", "i-12345",
                "--connection-type", "test",
            ],
            252,
            "argument --connection-type: Invalid choice, valid choices are:",
            id='Failure: Customer must provide connection-type when IP defined'
        ),

        pytest.param(
            [
                "ec2-instance-connect", "ssh",
                "--instance-id", "i-12345",
                "--connection-type", "direct",
                "--eice-options", "endpointId=eice-12345"
            ],
            252,
            "eice-options can't be specified when connection type is direct.",
            id='Failure: Customer can not use connection-type direct with eice-id'
        ),

        pytest.param(
            [
                "ec2-instance-connect", "ssh",
                "--instance-id", "i-12345",
                "--connection-type", "direct",
                "--eice-options", "dnsName=test.com"
            ],
            252,
            "eice-options can't be specified when connection type is direct.",
            id='Failure: Customer can not use connection-type direct with eice-dns-name'
        ),

        pytest.param(
            [
                "ec2-instance-connect", "ssh",
                "--instance-id", "i-12345",
                "--connection-type", "direct",
                "--eice-options", "maxTunnelDuration=12"
            ],
            252,
            "eice-options can't be specified when connection type is direct.",
            id='Failure: Customer can not use connection-type direct with maxTunnelDuration'
        ),

        pytest.param(
            [
                "ec2-instance-connect", "ssh",
                "--instance-id", "i-12345",
                "--eice-options", "dnsName=test"
            ],
            252,
            "When specifying dnsName, you must specify endpointId.",
            id='Failure: Customer must define eice-id when eice-dns provided'
        ),

        pytest.param(
            [
                "ec2-instance-connect", "ssh",
                "--instance-id", "i-12345",
                "--ssh-port", "ab"
            ],
            255,
            "invalid literal for int() with base 10",
            id='Failure: port must be int'
        ),

        pytest.param(
            [
                "ec2-instance-connect", "ssh",
                "--instance-id", "i-12345",
                "--eice-options", "maxTunnelDuration=ab"
            ],
            255,
            'invalid literal for int() with base 10',
            id='Failure: maxTunnelDuration must be int'
        ),

        pytest.param(
            [
                "ec2-instance-connect", "ssh",
                "--instance-id", "i-12345",
                "--instance-ip", "10.0.0.1"
            ],
            252,
            'When specifying instance-ip, you must specify connection-type.',
            id='Failure: Customer must define connection-type when ip define instead of Instance ID'
        ),

        pytest.param(
            [
                "ec2-instance-connect", "ssh",
                "--instance-id", "a-12345"
            ],
            252,
            'The specified instance ID is invalid.',
            id='Failure: Customer provide valid Instance ID'
        ),

        pytest.param(
            [
                "ec2-instance-connect", "ssh",
                "--instance-id", "i-12+3:4;5"
            ],
            252,
            'The specified instance ID is invalid.',
            id='Failure: Customer provide valid Instance ID without special characters'
        ),

        pytest.param(
            [
                "ec2-instance-connect", "ssh",
                "--instance-id", "i-12345",
                "--eice-options", "endpointId=aeice-12345"
            ],
            252,
            'The specified endpointId is invalid.',
            id='Failure: Customer must define valid EICE ID'
        ),

        pytest.param(
            [
                "ec2-instance-connect", "ssh",
                "--instance-id", "i-12345",
                "--eice-options", "endpointId=eice-12;3:4+5-"
            ],
            252,
            'The specified endpointId is invalid.',
            id='Failure: Customer must define valid EICE ID without special characters'
        ),

        pytest.param(
            [
                "ec2-instance-connect", "ssh",
                "--instance-id", "i-12345",
                "--eice-options", "endpointId=eice-12345,dnsName=dns.domain.+com",
            ],
            252,
            'The specified dnsName is invalid.',
            id='Failure: Customer must define valid EICE dnsName without special characters'
        ),

        pytest.param(
            [
                "ec2-instance-connect", "ssh",
                "--instance-id", "i-12345",
                "--eice-options", "test=123"
            ],
            252,
            'Unknown parameter in input',
            id="Failure: Customer must define allowed eice options"
        ),
    ])
    def test_command_fails_when_invalid_input(self, cli_runner, cli_input, expected_error_code, expected):
        result = cli_runner.run(cli_input)

        assert expected_error_code == result.rc
        assert expected in result.stderr

    @pytest.mark.parametrize("duration", ["-1", "0", "3601"])
    def test_command_fails_when_using_invalid_max_tunnel_duration(self, cli_runner, duration):
        cmdline = [
            "ec2-instance-connect", "ssh",
            "--instance-id", "i-123",
            "--eice-options", f"maxTunnelDuration={duration}"
        ]
        result = cli_runner.run(cmdline)

        assert 252 == result.rc
        assert "Invalid value specified for maxTunnelDuration. Value must be greater than 1 and less than 3600." \
               in result.stderr

    @mock.patch("shutil.which")
    @mock.patch.object(sys, 'argv', ['aws'])
    def test_command_error_when_ssh_not_available(self, mock_which, cli_runner,
                                                  describe_public_instance_response,
                                                  request_params_for_describe_instance):
        mock_which.return_value = None
        cli_runner.add_response(HTTPResponse(body=describe_public_instance_response))

        result = cli_runner.run([
            "ec2-instance-connect", "ssh",
            "--instance-id", "i-123",
            "--private-key-file", "/tmp/ssh-file",
        ])

        assert 253 == result.rc
        assert 'SSH not available.' in result.stderr
        assert result.aws_requests == [
            AWSRequest(
                service_name='ec2',
                operation_name='DescribeInstances',
                params=request_params_for_describe_instance,
            ),
        ]
