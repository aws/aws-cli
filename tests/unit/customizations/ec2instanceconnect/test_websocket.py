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
import platform
import socket
import struct
import sys
from io import TextIOWrapper, BytesIO
from threading import Event
from queue import Queue
from unittest import mock
from unittest.mock import patch
from urllib.parse import urlparse

import pytest
from awscrt import websocket
from awscrt.http import HttpProxyAuthenticationType, HttpProxyOptions, HttpRequest, HttpHeaders
from awscrt.io import ClientTlsContext, TlsContextOptions, TlsConnectionOptions
from awscrt.websocket import (
    Opcode,
    OnConnectionSetupData,
    OnIncomingFramePayloadData,
    IncomingFrame,
    OnSendFrameCompleteData,
    OnConnectionShutdownData,
    OnIncomingFrameCompleteData,
    WebSocket,
)

from awscli.customizations.ec2instanceconnect.websocket import (
    BaseWebsocketIO, Websocket, StdinStdoutIO, WindowsStdinStdoutIO,
    TCPSocketIO, WebsocketException, WebsocketManager, InputClosedError,
)


skip_if_windows = pytest.mark.skipif(
    platform.system() not in ['Darwin', 'Linux'],
    reason="This test does not run on windows.")
if_windows = pytest.mark.skipif(
    platform.system() in ['Darwin', 'Linux'],
    reason="This test only runs on windows.")


class TestWebsocketIO:

    def test_stdin_stdout_io_read(self, monkeypatch):
        io = StdinStdoutIO()

        expected_data = b"Test"
        monkeypatch.setattr('sys.stdin', TextIOWrapper(BytesIO(expected_data)))

        returned_data = io.read(100)

        assert returned_data == expected_data

    def test_stdin_stdout_io_write(self, monkeypatch):
        io = StdinStdoutIO()

        mock_text_io_wrapper = mock.Mock(spec=TextIOWrapper)
        monkeypatch.setattr('sys.stdout', mock_text_io_wrapper)

        expected_data = b"Test"
        io.write(expected_data)

        mock_text_io_wrapper.buffer.write.assert_called_with(expected_data)
        assert mock_text_io_wrapper.flush.called

    @skip_if_windows
    @mock.patch("select.select")
    def test_stdin_stdout_io_has_data_to_read_returns_false_non_windows(self, mock_select):
        io = StdinStdoutIO()

        expected_socket_list = [sys.stdin]

        mock_select.return_value = None, None, None

        return_val = io.has_data_to_read()

        mock_select.assert_called_with(expected_socket_list, [], [], 0.05)
        assert not return_val

    @skip_if_windows
    @mock.patch("select.select")
    def test_stdin_stdout_io_has_data_to_read_returns_true_non_windows(self, mock_select):
        io = StdinStdoutIO()

        expected_socket_list = [sys.stdin]

        mock_select.return_value = True, None, None

        return_val = io.has_data_to_read()

        mock_select.assert_called_with(expected_socket_list, [], [], 0.05)
        assert return_val

    @if_windows
    def test_windows_stdin_stdout_io_has_data_to_read_always_returns_true(self):
        io = WindowsStdinStdoutIO()
        assert io.has_data_to_read()

    def test_tcp_socket_io_read(self):
        mock_conn = mock.Mock(spec=socket.SocketType)
        io = TCPSocketIO(mock_conn)

        expected_data = b"Test"
        mock_conn.recv.return_value = expected_data

        bytes_to_read = 100
        returned_data = io.read(bytes_to_read)

        assert returned_data == expected_data
        mock_conn.recv.assert_called_with(bytes_to_read)

    def test_tcp_socket_io_write(self):
        mock_conn = mock.Mock(spec=socket.SocketType)
        io = TCPSocketIO(mock_conn)

        expected_data = b"Test"

        io.write(expected_data)

        mock_conn.sendall.assert_called_with(expected_data)


    def test_tcp_socket_io_read_raise_error_when_empty_data(self):
        mock_conn = mock.Mock(spec=socket.SocketType)
        io = TCPSocketIO(mock_conn)

        expected_data = b""
        mock_conn.recv.return_value = expected_data

        bytes_to_read = 100
        with pytest.raises(InputClosedError):
            io.read(bytes_to_read)

        mock_conn.recv.assert_called_with(bytes_to_read)

@pytest.fixture
def mock_websocketio():
    return mock.Mock(spec=BaseWebsocketIO)


@pytest.fixture
def mock_crt_websocket():
    return mock.Mock(spec=WebSocket)


@pytest.fixture
def mock_on_connection_event():
    return mock.Mock(spec=Event)


@pytest.fixture
def mock_send_frame_results_queue():
    return mock.Mock(spec=Queue)


@pytest.fixture
def mock_shutdown_event():
    return mock.Mock(spec=Event)


@pytest.fixture
def mock_tls_connection_options():
    return mock.Mock(spec=TlsConnectionOptions)


@pytest.fixture
def mock_handshake_request():
    return mock.Mock(spec=HttpRequest)


@pytest.fixture
def web_socket(mock_websocketio, mock_crt_websocket, mock_on_connection_event, mock_send_frame_results_queue,
               mock_shutdown_event, mock_tls_connection_options):
    web_socket = Websocket(mock_websocketio, "websocket-id", mock_tls_connection_options, mock_on_connection_event,
                           mock_shutdown_event, mock_send_frame_results_queue)
    web_socket._websocket = mock_crt_websocket
    return web_socket


def assert_websocket_closed(mock_shutdown_event, mock_crt_websocket, mock_websocketio):
    assert mock_shutdown_event.set.called
    assert mock_crt_websocket.close.called
    assert mock_websocketio.close.called


class CaptureCRTWebsocket:
    def __init__(self):
        self.on_connection_setup_handler = None
        self.on_connection_shutdown_handler = None
        self.on_incoming_frame_payload_handler = None
        self.on_incoming_frame_complete_handler = None

    def connect(self, **kwargs):
        self.on_connection_setup_handler = kwargs['on_connection_setup']
        self.on_connection_shutdown_handler = kwargs['on_connection_shutdown']
        self.on_incoming_frame_payload_handler = kwargs['on_incoming_frame_payload']
        self.on_incoming_frame_complete_handler = kwargs['on_incoming_frame_complete']


@pytest.fixture
def capture_crt_websocket():
    return CaptureCRTWebsocket()


@pytest.fixture
def websocket_url():
    return 'wss://amazon.com/openTunnel?params'


class TestWebsocket:
    @pytest.fixture(autouse=True)
    def patch_crt_websocket(self, monkeypatch, capture_crt_websocket):
        monkeypatch.setattr("awscrt.websocket.connect", capture_crt_websocket.connect)

    @patch.object(websocket, "connect")
    @patch.object(websocket, "create_handshake_request")
    def test_connect(
            self, mock_handshake, mock_connect, mock_handshake_request,
            mock_on_connection_event, mock_tls_connection_options, web_socket, websocket_url
    ):
        parsed_url = urlparse(websocket_url)
        host = parsed_url.hostname
        path = parsed_url.path + "?" + parsed_url.query
        mock_handshake.return_value = mock_handshake_request

        http_headers = HttpHeaders()
        mock_handshake_request.headers = http_headers

        web_socket.connect(websocket_url, 'defined-user-agent')

        mock_handshake.assert_called_with(host=host, path=path)
        mock_tls_connection_options.set_server_name.assert_called_with(host)
        assert 'defined-user-agent' == http_headers.get('User-Agent')
        mock_connect.assert_called_with(
            host=host,
            handshake_request=mock_handshake_request,
            port=443,
            tls_connection_options=mock_tls_connection_options,
            proxy_options=None,
            on_connection_setup=mock.ANY,
            on_connection_shutdown=mock.ANY,
            on_incoming_frame_payload=mock.ANY,
            on_incoming_frame_complete=mock.ANY
        )

        assert mock_on_connection_event.wait.called

    @patch.object(websocket, "connect")
    @patch.object(websocket, "create_handshake_request")
    @mock.patch.dict(os.environ, {"HTTPS_PROXY": "http://user1:pass1@localhost:8989", "NO_PROXY": "different-domain"})
    def test_connect_with_proxy(
            self, mock_handshake, mock_connect, mock_on_connection_event,
            mock_tls_connection_options, web_socket, websocket_url
    ):
        parsed_url = urlparse(websocket_url)
        host = parsed_url.hostname
        path = parsed_url.path + "?" + parsed_url.query
        mock_handshake.return_value = mock_handshake_request

        web_socket.connect(websocket_url)

        mock_handshake.assert_called_with(host=host, path=path)
        mock_tls_connection_options.set_server_name.assert_called_with(host)
        mock_connect.assert_called_with(
            host=host,
            handshake_request=mock_handshake_request,
            port=443,
            tls_connection_options=mock_tls_connection_options,
            proxy_options=mock.ANY,
            on_connection_setup=mock.ANY,
            on_connection_shutdown=mock.ANY,
            on_incoming_frame_payload=mock.ANY,
            on_incoming_frame_complete=mock.ANY
        )
        assert "localhost" == mock_connect.call_args.kwargs['proxy_options'].host_name
        assert 8989 == mock_connect.call_args.kwargs['proxy_options'].port
        assert HttpProxyAuthenticationType.Basic == mock_connect.call_args.kwargs['proxy_options'].auth_type
        assert "user1" == mock_connect.call_args.kwargs['proxy_options'].auth_username
        assert "pass1" == mock_connect.call_args.kwargs['proxy_options'].auth_password

        assert mock_on_connection_event.wait.called

    @patch.object(websocket, "connect")
    @patch.object(websocket, "create_handshake_request")
    @mock.patch.dict(os.environ, {"HTTPS_PROXY": "http://user1:pass1@localhost:8989"})
    def test_connect_with_proxy_but_no_proxy_env_empty(
            self, mock_handshake, mock_connect, mock_on_connection_event,
            mock_tls_connection_options, web_socket, websocket_url
    ):
        parsed_url = urlparse(websocket_url)
        host = parsed_url.hostname
        path = parsed_url.path + "?" + parsed_url.query
        mock_handshake.return_value = mock_handshake_request

        web_socket.connect(websocket_url)

        mock_handshake.assert_called_with(host=host, path=path)
        mock_tls_connection_options.set_server_name.assert_called_with(host)
        mock_connect.assert_called_with(
            host=host,
            handshake_request=mock_handshake_request,
            port=443,
            tls_connection_options=mock_tls_connection_options,
            proxy_options=mock.ANY,
            on_connection_setup=mock.ANY,
            on_connection_shutdown=mock.ANY,
            on_incoming_frame_payload=mock.ANY,
            on_incoming_frame_complete=mock.ANY
        )
        assert "localhost" == mock_connect.call_args.kwargs['proxy_options'].host_name
        assert 8989 == mock_connect.call_args.kwargs['proxy_options'].port
        assert HttpProxyAuthenticationType.Basic == mock_connect.call_args.kwargs['proxy_options'].auth_type
        assert "user1" == mock_connect.call_args.kwargs['proxy_options'].auth_username
        assert "pass1" == mock_connect.call_args.kwargs['proxy_options'].auth_password

        assert mock_on_connection_event.wait.called

    @patch.object(websocket, "connect")
    @patch.object(websocket, "create_handshake_request")
    @mock.patch.dict(os.environ,
                     {"HTTPS_PROXY": "http://user1:pass1@localhost:8989", "NO_PROXY": "1eice-123.eice.amazon.com"})
    def test_connect_with_proxy_define_and_no_proxy_defined(
            self, mock_handshake, mock_connect, mock_handshake_request,
            mock_on_connection_event, mock_tls_connection_options, web_socket
    ):
        url = "wss://eice-123.eice.amazon.com/openTunnel?params"
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        path = parsed_url.path + "?" + parsed_url.query
        mock_handshake.return_value = mock_handshake_request

        web_socket.connect(url)

        mock_handshake.assert_called_with(host=host, path=path)
        mock_tls_connection_options.set_server_name.assert_called_with(host)
        mock_connect.assert_called_with(
            host=host,
            handshake_request=mock_handshake_request,
            port=443,
            tls_connection_options=mock_tls_connection_options,
            proxy_options=None,
            on_connection_setup=mock.ANY,
            on_connection_shutdown=mock.ANY,
            on_incoming_frame_payload=mock.ANY,
            on_incoming_frame_complete=mock.ANY
        )

        assert mock_on_connection_event.wait.called

    def test_write_data_from_input_when_there_is_data_to_read(
            self, mock_websocketio, mock_crt_websocket, mock_send_frame_results_queue, mock_shutdown_event,
            web_socket, capture_crt_websocket
    ):
        data_as_bytes = b"Test"
        mock_websocketio.read.return_value = data_as_bytes
        mock_websocketio.has_data_to_read.return_value = True

        mock_shutdown_event.is_set.side_effect = [False, True]

        web_socket.write_data_from_input()

        mock_websocketio.read.assert_called_with(65_000)
        mock_crt_websocket.send_frame.assert_called_with(
            opcode=Opcode.BINARY,
            payload=data_as_bytes,
            on_complete=mock.ANY,
        )
        assert mock_send_frame_results_queue.get.called
        assert_websocket_closed(mock_shutdown_event, mock_crt_websocket, mock_websocketio)

    @mock.patch("time.sleep")
    def test_write_data_from_input_when_there_is_no_data_to_read(
            self, mock_sleep, mock_websocketio, mock_crt_websocket, mock_shutdown_event, web_socket
    ):
        mock_websocketio.has_data_to_read.return_value = False

        mock_shutdown_event.is_set.side_effect = [False, True]

        web_socket.write_data_from_input()

        mock_sleep.assert_called_with(0.05)

        assert_websocket_closed(mock_shutdown_event, mock_crt_websocket, mock_websocketio)

    def test_write_data_from_input_shuts_down_when_sends_frame_throws_close_frame_sent(
            self, mock_websocketio, mock_crt_websocket, mock_shutdown_event, web_socket
    ):
        mock_crt_websocket.send_frame.side_effect = RuntimeError(
            "AWS_ERROR_HTTP_WEBSOCKET_CLOSE_FRAME_SENT"
        )

        data_as_bytes = b"Test"
        mock_websocketio.read.return_value = data_as_bytes
        mock_websocketio.has_data_to_read.return_value = True
        mock_shutdown_event.is_set.side_effect = [False, True]

        web_socket.write_data_from_input()

        assert_websocket_closed(mock_shutdown_event, mock_crt_websocket, mock_websocketio)

    def test_write_data_northbound_shuts_down_when_sends_frame_throws_http_connection_closed(
            self, mock_websocketio, mock_crt_websocket, mock_shutdown_event, web_socket
    ):
        mock_crt_websocket.send_frame.side_effect = RuntimeError(
            "AWS_ERROR_HTTP_CONNECTION_CLOSED"
        )

        data_as_bytes = b"Test"
        mock_websocketio.read.return_value = data_as_bytes
        mock_websocketio.has_data_to_read.return_value = True
        mock_shutdown_event.is_set.side_effect = [False, True]

        web_socket.write_data_from_input()

        assert_websocket_closed(mock_shutdown_event, mock_crt_websocket, mock_websocketio)

    def test_on_connection_sets_websocket(self, capture_crt_websocket, websocket_url,
                                          mock_on_connection_event, web_socket):
        data = OnConnectionSetupData()
        data.websocket = mock.Mock(spec=Websocket)
        request_id = "request_id"
        data.handshake_response_headers = [("X-Amzn-RequestId", request_id)]

        web_socket.connect(websocket_url)
        capture_crt_websocket.on_connection_setup_handler(data)

        assert data.websocket == web_socket._websocket
        assert mock_on_connection_event.set.called

    def test_on_connection_with_exception(self, mock_on_connection_event, web_socket, websocket_url,
                                          capture_crt_websocket):
        data = OnConnectionSetupData()
        request_id = "request_id"
        data.handshake_response_headers = [("X-Amzn-RequestId", request_id)]
        data.exception = Exception()
        data.handshake_response_status = 401
        data.handshake_response_body = b"Failed to connect"

        web_socket.connect(websocket_url)
        capture_crt_websocket.on_connection_setup_handler(data)

        assert mock_on_connection_event.set.called

    def test_on_incoming_frame_payload_data_with_binary_frame(
            self, mock_websocketio, web_socket, websocket_url, capture_crt_websocket
    ):
        data_in_bytes = b"Test"
        frame = IncomingFrame(opcode=Opcode.BINARY, payload_length=len(data_in_bytes), fin=True)

        web_socket.connect(websocket_url)
        capture_crt_websocket.on_incoming_frame_payload_handler(
            OnIncomingFramePayloadData(data=data_in_bytes, frame=frame)
        )

        mock_websocketio.write.assert_called_with(data_in_bytes)

    def test_on_incoming_frame_payload_data_with_close_frame(
            self, web_socket, websocket_url, capture_crt_websocket
    ):
        data_in_bytes = b"Test"
        frame = IncomingFrame(opcode=Opcode.CLOSE, payload_length=len(data_in_bytes), fin=True)

        web_socket.connect(websocket_url)
        capture_crt_websocket.on_incoming_frame_payload_handler(
            OnIncomingFramePayloadData(data=data_in_bytes, frame=frame)
        )

        assert bytearray(data_in_bytes) == web_socket._close_frame_bytes

    def test_on_incoming_frame_payload_data_with_text_frame_sets_shutdown_event(
            self, mock_websocketio, mock_crt_websocket, mock_shutdown_event, web_socket,
            websocket_url, capture_crt_websocket
    ):
        data_in_bytes = b"Test"
        frame = IncomingFrame(opcode=Opcode.TEXT, payload_length=len(data_in_bytes), fin=True)

        web_socket.connect(websocket_url)
        capture_crt_websocket.on_incoming_frame_payload_handler(
            OnIncomingFramePayloadData(data=data_in_bytes, frame=frame)
        )

        assert isinstance(web_socket.exception, WebsocketException)

        assert_websocket_closed(mock_shutdown_event, mock_crt_websocket, mock_websocketio)

    def test_on_incoming_frame_complete_with_close_frame(
            self, mock_websocketio, mock_crt_websocket, mock_shutdown_event, web_socket,
            websocket_url, capture_crt_websocket
    ):

        shutdown_reason = b"Test"
        data_in_bytes = struct.pack(">H", 1) + shutdown_reason
        frame = IncomingFrame(opcode=Opcode.CLOSE, payload_length=len(shutdown_reason), fin=True)

        web_socket.connect(websocket_url)
        capture_crt_websocket.on_incoming_frame_payload_handler(
            OnIncomingFramePayloadData(frame=frame, data=data_in_bytes,)
        )
        capture_crt_websocket.on_incoming_frame_complete_handler(
            OnIncomingFrameCompleteData(frame=frame, exception=None)
        )

        expected_exc = WebsocketException(f"Websocket Closure Reason: {shutdown_reason.decode()}")
        assert isinstance(web_socket.exception, WebsocketException)
        # Ensure shutdown reason is decoded properly. (validate properties on WebsocketException)
        assert web_socket.exception.args == expected_exc.args
        assert_websocket_closed(mock_shutdown_event, mock_crt_websocket, mock_websocketio)

    def test_on_incoming_frame_complete_with_close_frame_ignores_shutdown_code_1000(
            self, mock_websocketio, mock_crt_websocket, mock_shutdown_event, web_socket,
            websocket_url, capture_crt_websocket
    ):
        frame = IncomingFrame(opcode=Opcode.CLOSE, payload_length=0, fin=True)
        incoming_frame_data = OnIncomingFrameCompleteData(frame=frame)

        web_socket.connect(websocket_url)
        capture_crt_websocket.on_incoming_frame_complete_handler(incoming_frame_data)

        assert not web_socket.exception
        assert_websocket_closed(mock_shutdown_event, mock_crt_websocket, mock_websocketio)

    def test_on_connection_shutdown(self, mock_websocketio, mock_crt_websocket, mock_shutdown_event,
                                    web_socket, websocket_url, capture_crt_websocket):
        data = OnConnectionShutdownData()

        web_socket.connect(websocket_url)
        capture_crt_websocket.on_connection_shutdown_handler(data)

        assert_websocket_closed(mock_shutdown_event, mock_crt_websocket, mock_websocketio)
