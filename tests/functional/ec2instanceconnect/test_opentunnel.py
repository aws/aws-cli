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
import concurrent.futures
import contextlib
import ctypes
import os
import queue
import socket
import struct
import sys
import threading
import time
import urllib.parse
import traceback
from typing import Optional, Callable, Union
from unittest import mock
import datetime

from dateutil.tz import tzutc
import awscrt
import pytest
from awscrt.http import HttpRequest, HttpProxyOptions
from awscrt.io import ClientBootstrap, SocketOptions, TlsConnectionOptions
from awscrt.websocket import OnConnectionSetupData, OnConnectionShutdownData, OnIncomingFramePayloadData, \
    OnIncomingFrameCompleteData, IncomingFrame, Opcode, OnSendFrameCompleteData, OnIncomingFrameBeginData
from awscli.customizations.ec2instanceconnect.websocket import WebsocketManager

from awscli.compat import is_windows
from awscli.customizations.ec2instanceconnect.websocket import BaseWebsocketIO
from tests import SessionStubber, AWSRequest, CLIRunner, HTTPResponse

STDIN_QUEUE = queue.Queue()
STDOUT_QUEUE = queue.Queue()
SHUTDOWN_SENTINEL = object()


class StubStdinStdoutIO(BaseWebsocketIO):

    def has_data_to_read(self):
        return not STDIN_QUEUE.empty()

    def read(self, amt) -> bytes:
        return STDIN_QUEUE.get()

    def write(self, data):
        STDOUT_QUEUE.put(data)

    def close(self):
        pass


def pop_stdout_content():
    return STDOUT_QUEUE.get(block=False)


def assert_stdout_empty():
    assert STDOUT_QUEUE.empty()


class MockCRTWebsocket(threading.Thread):

    def __init__(self):
        super().__init__()
        self.url = None
        self.client_input_queue = queue.Queue()
        self._server_input_queue = queue.Queue()
        self._shutdown_event = threading.Event()

        # Callbacks that get set when connect is called
        self._on_connection_setup = None
        self._on_connection_shutdown = None
        self._on_incoming_frame_begin = None
        self._on_incoming_frame_payload = None
        self._on_incoming_frame_complete = None

        self._shutdown_reason = None
        self._shutdown_exception = None

    def connect(
            self,
            *,
            host: str,
            port: Optional[int] = None,
            handshake_request: HttpRequest,
            bootstrap: Optional[ClientBootstrap] = None,
            socket_options: Optional[SocketOptions] = None,
            tls_connection_options: Optional[TlsConnectionOptions] = None,
            proxy_options: Optional[HttpProxyOptions] = None,
            manage_read_window: bool = False,
            initial_read_window: Optional[int] = None,
            on_connection_setup: Callable[[OnConnectionSetupData], None],
            on_connection_shutdown: Optional[Callable[[OnConnectionShutdownData], None]] = None,
            on_incoming_frame_begin: Optional[Callable[[OnIncomingFrameBeginData], None]] = None,
            on_incoming_frame_payload: Optional[Callable[[OnIncomingFramePayloadData], None]] = None,
            on_incoming_frame_complete: Optional[Callable[[OnIncomingFrameCompleteData], None]] = None,
    ):
        self.url = host + handshake_request.path

        self._on_connection_setup = on_connection_setup
        self._on_connection_shutdown = on_connection_shutdown
        self._on_incoming_frame_begin = on_incoming_frame_begin
        self._on_incoming_frame_payload = on_incoming_frame_payload
        self._on_incoming_frame_complete = on_incoming_frame_complete

        crt_websocket = mock.Mock(awscrt.websocket.WebSocket)
        crt_websocket.send_frame = self.send_frame_from_client
        data = OnConnectionSetupData()
        data.handshake_response_headers = []
        data.websocket = crt_websocket
        self._on_connection_setup(data)

        # Kick off thread that mocks reading and writing to the client.
        self.start()

    # Appends data to the server_input_queue, which will represent the server sending data to the websocket
    def add_output_from_server(self, data_in_bytes):
        self._server_input_queue.put(data_in_bytes)

    # Appends data to the client_input_queue, which will represent the client sending data to the websocket
    def send_frame_from_client(
            self,
            opcode: Opcode,
            payload: Optional[Union[str, bytes, bytearray, memoryview]] = None,
            *,
            fin: bool = True,
            on_complete: Optional[Callable[[OnSendFrameCompleteData], None]] = None,
    ):
        if opcode == Opcode.BINARY:
            data = OnSendFrameCompleteData()
            on_complete(data)
            if len(payload) > 0:
                self.client_input_queue.put(payload)

    def add_shutdown_from_server(self, shutdown_reason=None, shutdown_exception=None):
        self._server_input_queue.put(SHUTDOWN_SENTINEL)
        self._shutdown_reason = shutdown_reason
        self._shutdown_exception = shutdown_exception

    def run(self):
        while not self._shutdown_event.is_set():

            if not self._server_input_queue.empty():
                data_in_bytes = self._server_input_queue.get()
                if data_in_bytes == SHUTDOWN_SENTINEL:
                    self._shutdown_event.set()
                else:
                    incoming_frame = IncomingFrame(opcode=Opcode.BINARY, payload_length=len(data_in_bytes), fin=True)
                    payload_data = OnIncomingFramePayloadData(frame=incoming_frame, data=data_in_bytes)
                    self._on_incoming_frame_payload(payload_data)

                    complete_data = OnIncomingFrameCompleteData(frame=incoming_frame)
                    self._on_incoming_frame_complete(complete_data)

        if self._shutdown_reason:
            shutdown_code = 1
            packed_shutdown_code = struct.pack(">H", shutdown_code)
            encoded_shutdown_reason = self._shutdown_reason.encode()
            data_in_bytes = packed_shutdown_code + encoded_shutdown_reason
            incoming_frame = IncomingFrame(opcode=Opcode.CLOSE, payload_length=len(data_in_bytes), fin=True)
            payload_data = OnIncomingFramePayloadData(frame=incoming_frame, data=data_in_bytes)
            self._on_incoming_frame_payload(payload_data)

            complete_data = OnIncomingFrameCompleteData(frame=incoming_frame)
            self._on_incoming_frame_complete(complete_data)

        self._on_connection_shutdown(OnConnectionShutdownData(exception=self._shutdown_exception))


@pytest.fixture
def session_stubber():
    return SessionStubber()


@pytest.fixture
def region():
    return "us-west-2"


@pytest.fixture
def cli_runner(session_stubber, region):
    cli_runner = CLIRunner(session_stubber=session_stubber)
    cli_runner.env["AWS_DEFAULT_REGION"] = region
    return cli_runner


@pytest.fixture(autouse=True)
def clean_io_queues():
    while not STDIN_QUEUE.empty():
        STDIN_QUEUE.get()
    while not STDOUT_QUEUE.empty():
        STDOUT_QUEUE.get()


@pytest.fixture
def io_patch():
    io_to_patch = "WindowsStdinStdoutIO" if is_windows else "StdinStdoutIO"
    new_websocket_io = StubStdinStdoutIO
    return mock.patch(
        f"awscli.customizations.ec2instanceconnect.websocket.{io_to_patch}",
        new=new_websocket_io
    )


@pytest.fixture
def mock_crt_websocket():
    return MockCRTWebsocket()


@pytest.fixture
def connect_patch(mock_crt_websocket):
    return mock.patch("awscrt.websocket.connect", new=mock_crt_websocket.connect)


@pytest.fixture
def describe_instance_response():
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
def request_params_for_describe_instance():
    return {'InstanceIds': ['i-123']}


@pytest.fixture
def dns_name():
    return "eice-123.ec2-instance-connect-endpoint.us-west-2.amazonaws.com"

@pytest.fixture
def fips_dns_name():
    return "eice-123.fips.ec2-instance-connect-endpoint.us-west-2.amazonaws.com"

@pytest.fixture
def describe_eice_response(dns_name, fips_dns_name):
    return f"""
    <DescribeInstanceConnectEndpointsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
        <instanceConnectEndpointSet>
            <item>
                <dnsName>{dns_name}</dnsName>
                <fipsDnsName>{fips_dns_name}</fipsDnsName>
                <instanceConnectEndpointId>eice-123</instanceConnectEndpointId>
                <state>create-complete</state>
                <subnetId>subnet-123</subnetId>
                <vpcId>vpc-123</vpcId>
            </item>
        </instanceConnectEndpointSet>
    </DescribeInstanceConnectEndpointsResponse>
    """

@pytest.fixture
def describe_eice_response_without_fips_dns(dns_name, fips_dns_name):
    return f"""
    <DescribeInstanceConnectEndpointsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
        <instanceConnectEndpointSet>
            <item>
                <dnsName>{dns_name}</dnsName>
                <instanceConnectEndpointId>eice-123</instanceConnectEndpointId>
                <state>create-complete</state>
                <subnetId>subnet-123</subnetId>
                <vpcId>vpc-123</vpcId>
            </item>
        </instanceConnectEndpointSet>
    </DescribeInstanceConnectEndpointsResponse>
    """

@pytest.fixture
def describe_eice_response_empty_fips_dns(dns_name, fips_dns_name):
    return f"""
    <DescribeInstanceConnectEndpointsResponse xmlns="http://ec2.amazonaws.com/doc/2016-11-15/">
        <instanceConnectEndpointSet>
            <item>
                <dnsName>{dns_name}</dnsName>
                <fipsDnsName></fipsDnsName>
                <instanceConnectEndpointId>eice-123</instanceConnectEndpointId>
                <state>create-complete</state>
                <subnetId>subnet-123</subnetId>
                <vpcId>vpc-123</vpcId>
            </item>
        </instanceConnectEndpointSet>
    </DescribeInstanceConnectEndpointsResponse>
    """

@pytest.fixture
def request_params_for_describe_eice():
    return {'Filters': [{'Name': 'state', 'Values': ['create-complete']}, {'Name': 'vpc-id', 'Values': ['vpc-123']}]}


@pytest.fixture
def datetime_utcnow_patch():
    clock = datetime.datetime(2020, 1, 1, 1, 1, 1, tzinfo=tzutc())
    with mock.patch('datetime.datetime') as dt:
        dt.utcnow.return_value = clock
        yield dt


@pytest.fixture
def run_listener_cmd_in_thread_executor(
        cli_runner, mock_crt_websocket, connect_patch, io_patch
    ):
    stop_event = threading.Event()
    with mock.patch.object(WebsocketManager, 'RUNNING', new_callable=mock.PropertyMock) as websocket_join:
        websocket_join.return_value = stop_event
        with connect_patch, io_patch:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                def submit_run_command(cmdline):
                    return executor.submit(cli_runner.run, cmdline)
                yield submit_run_command
                stop_event.set()


def connect_to_listener(listener_future):
    retry_connection = True
    attempts = 0
    max_attempts = 5
    tracebacks = ''
    while retry_connection:
        attempts += 1
        time.sleep(0.2)
        try:
            return socket.create_connection(("localhost", 3333), timeout=5)
        except (ConnectionError, OSError) as e:
            tracebacks += f'Traceback from attempt {attempts}:\n{traceback.format_exc()}\n'
            if attempts == max_attempts:
                retry_connection = False
        except Exception as e:
            tracebacks += f'Traceback from attempt {attempts}:\n{traceback.format_exc()}\n'
            retry_connection = False
    msg = (
        f'Failed to connect to open-tunnel command after {attempts} attempts.\n'
        f'{tracebacks}'
    )
    if listener_future.done():
        cli_runner_result = listener_future.result()
        msg += (
            f'RC from open-tunnel cmd: {cli_runner_result.rc}\n'
            f'Stdout from open-tunnel cmd: {cli_runner_result.stdout}\n'
            f'Stderr from open-tunnel cmd: {cli_runner_result.stderr}'
        )
    assert False, msg


def assert_url(dns_name, url):
    _, _, path, _, qs, _ = urllib.parse.urlparse(url)
    parsed_qs = urllib.parse.parse_qs(qs)

    assert path == f"{dns_name}/openTunnel"
    assert parsed_qs["instanceConnectEndpointId"]
    assert parsed_qs["remotePort"]
    assert parsed_qs["privateIpAddress"]
    assert parsed_qs["maxTunnelDuration"]
    assert parsed_qs["X-Amz-Algorithm"]
    assert parsed_qs["X-Amz-Credential"]
    assert parsed_qs["X-Amz-Date"]
    assert parsed_qs["X-Amz-SignedHeaders"]
    assert parsed_qs["X-Amz-Signature"]
    assert parsed_qs["X-Amz-Expires"] == ["60"]


class TestOpenTunnel:

    def test_single_connection_mode(
            self,
            cli_runner,
            mock_crt_websocket,
            connect_patch,
            io_patch,
            describe_instance_response,
            dns_name,
            describe_eice_response,
            request_params_for_describe_instance,
            request_params_for_describe_eice,
            datetime_utcnow_patch,
    ):
        cli_runner.env["AWS_USE_FIPS_ENDPOINT"] = "false"
        cmdline = [
            "ec2-instance-connect", "open-tunnel",
            "--instance-id", "i-123",
            "--max-tunnel-duration", "1"
        ]
        cli_runner.add_response(HTTPResponse(body=describe_instance_response))
        cli_runner.add_response(HTTPResponse(body=describe_eice_response))

        test_server_input = b"Test Server Output"
        mock_crt_websocket.add_output_from_server(test_server_input)
        mock_crt_websocket.add_shutdown_from_server()

        with connect_patch, io_patch:
            result = cli_runner.run(cmdline)

        assert 0 == result.rc
        assert pop_stdout_content() == test_server_input
        assert_stdout_empty()
        # Order of the query params on the url mater because of sigv4
        assert "eice-123.ec2-instance-connect-endpoint.us-west-2.amazonaws.com/openTunnel?" \
               "instanceConnectEndpointId=eice-123&remotePort=22&privateIpAddress=10.0.0.0&" \
               "maxTunnelDuration=1&X-Amz-Algorithm=AWS4-HMAC-SHA256&" \
               "X-Amz-Credential=access_key%2F20200101%2Fus-west-2%2Fec2-instance-connect%2Faws4_request&" \
               "X-Amz-Date=20200101T010101Z&X-Amz-Expires=60&X-Amz-SignedHeaders=host&" \
               "X-Amz-Signature=3a56740422a5b9aebd22d860b7a30c729e459a6f71a83bc0de3a2b44b7353f28" == \
               mock_crt_websocket.url
        assert_url(dns_name, mock_crt_websocket.url)
        assert result.aws_requests == [
            AWSRequest(
                service_name='ec2',
                operation_name='DescribeInstances',
                params=request_params_for_describe_instance,
            ),
            AWSRequest(
                service_name='ec2',
                operation_name='DescribeInstanceConnectEndpoints',
                params=request_params_for_describe_eice,
            )
        ]

    def test_single_connection_mode_with_no_describe_calls(
            self,
            cli_runner,
            mock_crt_websocket,
            connect_patch,
            io_patch,
            dns_name,
    ):
        cmdline = [
            "ec2-instance-connect", "open-tunnel",
            "--private-ip-address", "10.0.0.0",
            "--instance-connect-endpoint-id", "eice-123",
            "--instance-connect-endpoint-dns-name", dns_name,
            "--max-tunnel-duration", "1"
        ]

        test_server_input = b"Test Server Output"
        mock_crt_websocket.add_output_from_server(test_server_input)
        mock_crt_websocket.add_shutdown_from_server()

        with connect_patch, io_patch:
            result = cli_runner.run(cmdline)

        assert 0 == result.rc
        assert pop_stdout_content() == test_server_input
        assert_stdout_empty()
        assert_url(dns_name, mock_crt_websocket.url)
        assert result.aws_requests == []


    def test_multiple_connection_mode(
            self,
            run_listener_cmd_in_thread_executor,
            mock_crt_websocket,
    ):
        cmdline = [
            "ec2-instance-connect", "open-tunnel",
            "--instance-id", "i-123",
            "--private-ip-address", "10.0.0.0",
            "--instance-connect-endpoint-id", "eice-123",
            "--instance-connect-endpoint-dns-name", "test",
            "--local-port", "3333"
        ]
        future = run_listener_cmd_in_thread_executor(cmdline)
        # Retry several times since it can take few ms to set up everything
        with contextlib.closing(connect_to_listener(future)) as s:
            test_server_input = b"Test Server Output"
            mock_crt_websocket.add_output_from_server(test_server_input)

            # Reading from the TCP Conn should return test server input
            data = s.recv(1024)
            assert test_server_input == data

            test_client_input = b"Test Client Input"
            # Writing to the TCP Conn should ensure a frame is sent with that data
            s.sendall(test_client_input)
            client_input_sent_to_websocket = mock_crt_websocket.client_input_queue.get(timeout=5)
            assert test_client_input == client_input_sent_to_websocket

            mock_crt_websocket.add_shutdown_from_server()

    def test_command_uses_fips_endpoint_to_connect(
            self, cli_runner, mock_crt_websocket, connect_patch, io_patch, describe_instance_response,
            fips_dns_name, describe_eice_response,
    ):
        cli_runner.env["AWS_USE_FIPS_ENDPOINT"] = "true"
        cmdline = [
            "ec2-instance-connect", "open-tunnel",
            "--instance-id", "i-123",
            "--max-tunnel-duration", "1"
        ]
        cli_runner.add_response(HTTPResponse(body=describe_instance_response))
        cli_runner.add_response(HTTPResponse(body=describe_eice_response))


        test_server_input = b"Test Server Output"
        mock_crt_websocket.add_output_from_server(test_server_input)
        mock_crt_websocket.add_shutdown_from_server()

        with connect_patch, io_patch:
            result = cli_runner.run(cmdline)

        assert 0 == result.rc
        assert_url(fips_dns_name, mock_crt_websocket.url)

    def test_command_returns_shutdown_reason(
            self, cli_runner, mock_crt_websocket, connect_patch, io_patch
    ):
        cmdline = [
            "ec2-instance-connect", "open-tunnel",
            "--instance-id", "i-123",
            "--private-ip-address", "10.0.0.0",
            "--instance-connect-endpoint-id", "eice-123",
            "--instance-connect-endpoint-dns-name", "test"
        ]

        shutdown_reason = "Test Shutdown"
        mock_crt_websocket.add_shutdown_from_server(shutdown_reason=shutdown_reason)

        with connect_patch, io_patch:
            result = cli_runner.run(cmdline)

        assert 255 == result.rc
        assert shutdown_reason in result.stderr

    def test_command_returns_shutdown_exception(
            self, cli_runner, mock_crt_websocket, connect_patch, io_patch
    ):
        cmdline = [
            "ec2-instance-connect", "open-tunnel",
            "--instance-id", "i-123",
            "--private-ip-address", "10.0.0.0",
            "--instance-connect-endpoint-id", "eice-123",
            "--instance-connect-endpoint-dns-name", "test"
        ]

        shutdown_exception_message = "Test Shutdown Error"
        mock_crt_websocket.add_shutdown_from_server(shutdown_exception=RuntimeError(shutdown_exception_message))

        with connect_patch, io_patch:
            result = cli_runner.run(cmdline)

        assert 255 == result.rc
        assert shutdown_exception_message in result.stderr

    @pytest.mark.parametrize("cli_input,expected", [
        # Customer must provide instance id or private ip
        (
                [
                    "ec2-instance-connect", "open-tunnel",
                    "--instance-connect-endpoint-id", "eice-123",
                    "--instance-connect-endpoint-dns-name", "test"
                ],
                "Specify an instance id or private ip"
        ),
        # Customer must define eice id when dns name is provided
        (
                [
                    "ec2-instance-connect", "open-tunnel",
                    "--instance-id", "i-123",
                    "--instance-connect-endpoint-dns-name", "test"
                ],
                "Specify an instance connect endpoint id"
        ),
        # Customer must define eice id when private ip is provided
        (
                [
                    "ec2-instance-connect", "open-tunnel",
                    "--instance-id", "i-123",
                    "--private-ip-address", "0.0.0.0"
                ],
                "Specify an instance connect endpoint id"
        ),
        # Customer must use provide local port when using command in isatty mode
        (
                [
                    "ec2-instance-connect", "open-tunnel",
                    "--instance-id", "i-123"
                ],
                "This command does not support interactive mode"
        )
    ])
    @mock.patch("sys.stdin")
    def test_command_fails_when_invalid_input(self, mock_stdin, cli_runner, cli_input, expected):
        mock_stdin.isatty.return_value = True
        result = cli_runner.run(cli_input)

        assert 252 == result.rc
        assert expected in result.stderr

    @pytest.mark.parametrize("duration", ["-1", "0", "3601"])
    def test_command_fails_when_using_invalid_max_tunnel_duration(self, cli_runner, duration):
        cmdline = [
            "ec2-instance-connect", "open-tunnel",
            "--instance-id", "i-123",
            "--max-tunnel-duration", duration
        ]
        result = cli_runner.run(cmdline)

        assert 252 == result.rc
        assert "Invalid max connection timeout specified" in result.stderr

    def test_command_fails_when_no_fips_endpoint_available_to_connect(
            self, cli_runner, describe_instance_response, describe_eice_response_without_fips_dns,
    ):
        cli_runner.env["AWS_USE_FIPS_ENDPOINT"] = "true"
        cmdline = [
            "ec2-instance-connect", "open-tunnel",
            "--instance-id", "i-123",
            "--max-tunnel-duration", "1"
        ]
        cli_runner.add_response(HTTPResponse(body=describe_instance_response))
        cli_runner.add_response(HTTPResponse(body=describe_eice_response_without_fips_dns))

        result = cli_runner.run(cmdline)

        assert 253 == result.rc
        assert "Unable to find FIPS Endpoint" in result.stderr

    def test_command_fails_when_empty_fips_endpoint_available_to_connect(
                self, cli_runner, describe_instance_response, describe_eice_response_empty_fips_dns,
        ):
            cli_runner.env["AWS_USE_FIPS_ENDPOINT"] = "true"
            cmdline = [
                "ec2-instance-connect", "open-tunnel",
                "--instance-id", "i-123",
                "--max-tunnel-duration", "1"
            ]
            cli_runner.add_response(HTTPResponse(body=describe_instance_response))
            cli_runner.add_response(HTTPResponse(body=describe_eice_response_empty_fips_dns))

            result = cli_runner.run(cmdline)

            assert 253 == result.rc
            assert "Unable to find FIPS Endpoint" in result.stderr
