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
import os
import select
import socket
import struct
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from queue import Queue
from threading import Event
from urllib.parse import urlparse

from awscrt import websocket
from awscrt.http import HttpProxyAuthenticationType, HttpProxyOptions
from awscrt.io import ClientTlsContext, TlsContextOptions
from awscrt.websocket import (
    OnConnectionSetupData,
    OnConnectionShutdownData,
    OnIncomingFrameCompleteData,
    OnIncomingFramePayloadData,
    OnSendFrameCompleteData,
    Opcode,
)

from awscli.compat import is_windows

logger = logging.getLogger(__name__)


class WebsocketException(RuntimeError):
    pass


class InputClosedError(RuntimeError):
    pass


class BaseWebsocketIO:
    def has_data_to_read(self):
        raise NotImplementedError("has_data_to_read")

    def read(self, amt) -> bytes:
        raise NotImplementedError("read")

    def write(self, data):
        raise NotImplementedError("write")

    def close(self):
        raise NotImplementedError("close")


_SELECT_TIMEOUT = 0.05


class StdinStdoutIO(BaseWebsocketIO):
    def has_data_to_read(self):
        socket_list = [sys.stdin]
        read_sockets, _, _ = select.select(
            socket_list, [], [], _SELECT_TIMEOUT
        )
        if read_sockets:
            return True
        return False

    def read(self, amt) -> bytes:
        try:
            data = sys.stdin.buffer.read1(amt)
            # Empty data indicates EOF (pipe closed)
            if not data:
                logger.debug("Stdin returned empty data (EOF). Input is closed.")
                raise InputClosedError()
            return data
        except (OSError, IOError) as e:
            logger.debug(f"IO error reading from stdin: {str(e)}")
            raise InputClosedError()

    def write(self, data):
        sys.stdout.buffer.write(data)
        sys.stdout.flush()

    def close(self):
        pass


class WindowsStdinStdoutIO(StdinStdoutIO):
    def has_data_to_read(self):
        # For Windows, we can't reliably check stdin without blocking
        # We'll rely on the read method to detect when input is closed
        # by catching EOF errors in the calling code
        try:
            if sys.stdin.closed:
                return False
            return True
        except (OSError, ValueError, IOError):
            return False


class TCPSocketIO(BaseWebsocketIO):
    def __init__(self, conn):
        self.conn = conn
        self._is_closed = False

    def has_data_to_read(self):
        if self._is_closed:
            return False

        # Use select with a timeout to check if there's data
        try:
            read_ready, _, _ = select.select([self.conn], [], [], _SELECT_TIMEOUT)
            return bool(read_ready)
        except (OSError, ValueError, socket.error):
            self._is_closed = True
            return False

    def read(self, amt) -> bytes:
        try:
            data = self.conn.recv(amt)
            # In listener mode use can CTRL+C during host verification that kills the client TCP connect,
            # when this happens we are able to successfully disconnect because has_data_to_read always return true.
            # This will check if data is empty and if yes then raise InputCloseError
            #
            # recv() relies on the underlying system call which returns empty bytes when the connection is closed.
            # Linux: https://manpages.debian.org/bullseye/manpages-dev/recv.2.en.html
            # Windows: https://learn.microsoft.com/en-us/windows/win32/api/winsock/nf-winsock-recv
            if not data:
                self._is_closed = True
                raise InputClosedError()
            return data
        except (OSError, socket.error):
            self._is_closed = True
            raise InputClosedError()

    def write(self, data):
        if self._is_closed:
            raise InputClosedError()
        try:
            self.conn.sendall(data)
        except (OSError, socket.error):
            self._is_closed = True
            raise InputClosedError()

    def close(self):
        if not self._is_closed:
            self._is_closed = True
            try:
                self.conn.shutdown(socket.SHUT_RDWR)
                self.conn.close()
            # On Windows, we could receive an OSError if the tcp conn is already closed.
            except OSError:
                pass


class Websocket:
    def __init__(
        self,
        websocketio,
        websocket_id,
        tls_connection_options=None,
        on_connection_event=None,
        shutdown_event=None,
        send_frame_results_queue=None,
    ):
        self.websocketio = websocketio
        self.websocket_id = websocket_id
        self._on_connection_event = (
            Event() if (on_connection_event is None) else on_connection_event
        )
        self._send_frame_results_queue = (
            Queue()
            if (send_frame_results_queue is None)
            else send_frame_results_queue
        )
        self._shutdown_event = (
            Event() if (shutdown_event is None) else shutdown_event
        )
        self._websocket = None
        self._exception = None
        self._close_frame_bytes = bytearray()

        if tls_connection_options is None:
            self._tls_connection_options = ClientTlsContext(
                TlsContextOptions()
            ).new_connection_options()
        else:
            self._tls_connection_options = tls_connection_options

    _MAX_BYTES_PER_FRAME = 65_000
    _WAIT_INTERVAL_FOR_INPUT = 0.05

    @property
    def exception(self):
        return self._exception

    def connect(self, url, user_agent=None):
        parsed_url = urlparse(url)
        path = parsed_url.path + "?" + parsed_url.query
        request = websocket.create_handshake_request(
            host=parsed_url.hostname, path=path
        )
        if user_agent:
            request.headers.set("User-Agent", user_agent)

        environment = os.environ.copy()
        proxy_options = None
        proxy_url = environment.get("HTTP_PROXY") or environment.get(
            "HTTPS_PROXY"
        )
        no_proxy = environment.get("NO_PROXY", "")
        if proxy_url and parsed_url.hostname not in no_proxy:
            parsed_proxy_url = urlparse(proxy_url)
            logger.debug(
                f"Using the following proxy: {parsed_proxy_url.hostname}"
            )
            proxy_options = HttpProxyOptions(
                host_name=parsed_proxy_url.hostname,
                port=parsed_proxy_url.port,
                auth_type=HttpProxyAuthenticationType.Basic
                if proxy_url
                else HttpProxyAuthenticationType.Nothing,
                auth_username=parsed_proxy_url.username or None,
                auth_password=parsed_proxy_url.password or None,
            )

        self._tls_connection_options.set_server_name(parsed_url.hostname)
        websocket.connect(
            host=parsed_url.hostname,
            handshake_request=request,
            port=443,
            tls_connection_options=self._tls_connection_options,
            proxy_options=proxy_options,
            on_connection_setup=self._on_connection,
            on_connection_shutdown=self._on_connection_shutdown,
            on_incoming_frame_payload=self._on_incoming_frame_payload_data,
            on_incoming_frame_complete=self._on_incoming_frame_complete,
        )

        # Wait for the on_connection callback to be called.
        self._on_connection_event.wait()

        if not self._websocket:
            self.close()
            raise self._exception

    def write_data_from_input(self):
        try:
            # Start writing data to the websocket connection and block current thread.
            self._write_data_from_input()
        except Exception as e:
            logger.error(f"Unexpected error in write_data_from_input: {str(e)}")
        finally:
            # Make sure to clean up on exit
            logger.debug("Exiting write_data_from_input, cleaning up")
            self.close()

            # If we're a stdin/stdout websocket and input was closed,
            # ensure the process exits cleanly
            if isinstance(self.websocketio, StdinStdoutIO) or isinstance(self.websocketio, WindowsStdinStdoutIO):
                logger.debug("Stdin/stdout websocket closed, exiting process")
                # This is a bit drastic but necessary to ensure the process exits
                # when stdin is closed in pipe mode
                import os
                import signal
                # Send SIGTERM to ourselves to initiate clean shutdown
                # This is more reliable than sys.exit() which can be caught
                os.kill(os.getpid(), signal.SIGTERM)

        if self._exception:
            raise self._exception

    def close(self):
        if self._websocket:
            self._websocket.close()
        self.websocketio.close()
        self._shutdown_event.set()

    def _write_data_from_input(self):
        while not self._shutdown_event.is_set():
            # Check if websocket is still valid
            if not self._websocket:
                logger.debug('Websocket is closed or invalid. Exiting write loop.')
                self.close()
                return

            # Wait until there's some data to read
            try:
                if not self.websocketio.has_data_to_read():
                    time.sleep(self._WAIT_INTERVAL_FOR_INPUT)
                    continue
            except Exception as e:
                logger.debug(f'Error checking for data: {str(e)}. Shutting down websocket.')
                self.close()
                return

            try:
                data = self.websocketio.read(self._MAX_BYTES_PER_FRAME)
                # Skip empty data (shouldn't happen, but as a safeguard)
                if not data:
                    logger.debug('Received empty data. Skipping frame.')
                    continue
            except InputClosedError:
                logger.debug('Input closed. Shutting down websocket.')
                self.close()
                return
            except Exception as e:
                logger.debug(f'Error reading data: {str(e)}. Shutting down websocket.')
                self.close()
                return

            try:
                self._websocket.send_frame(
                    opcode=Opcode.BINARY,
                    payload=data,
                    on_complete=self._on_send_frame_complete_data,
                )
                # Block until send_frame on_complete with a timeout
                try:
                    result = self._send_frame_results_queue.get(timeout=5.0)
                    if result and hasattr(result, 'exception') and result.exception:
                        raise result.exception
                except Exception as e:
                    logger.debug(f'Timeout or error waiting for frame completion: {str(e)}')
                    self.close()
                    return
            except RuntimeError as e:
                crt_exceptions = [
                    "AWS_ERROR_HTTP_WEBSOCKET_CLOSE_FRAME_SENT",
                    "AWS_ERROR_HTTP_CONNECTION_CLOSED",
                ]
                # Expected exception if server or user closes conn. Catch it and gracefully exit this method.
                if any(exc_code in str(e.args) for exc_code in crt_exceptions):
                    logger.debug(
                        f"Received exception when sending websocket frame: {e.args}"
                    )
                    self.close()
                    return
                else:
                    logger.debug(f"Unhandled runtime error: {e.args}")
                    self.close()
                    raise e
            except Exception as e:
                logger.debug(f'Unexpected error sending frame: {str(e)}')
                self.close()
                return

    def _on_connection(self, data: OnConnectionSetupData) -> None:
        request_id_header = [
            header
            for header in data.handshake_response_headers
            if any("x-amzn-requestid" == key.lower() for key in header)
        ]
        if request_id_header:
            logger.debug(f"OpenTunnel RequestId: {request_id_header[0][1]}")
        if data.exception:
            if data.handshake_response_status:
                logger.debug(f"Status code: {data.handshake_response_status}")
            if data.handshake_response_body:
                decoded_response = data.handshake_response_body.decode("utf-8")
                logger.error(decoded_response)
            self._exception = data.exception
        self._websocket = data.websocket
        self._on_connection_event.set()

    def _on_incoming_frame_payload_data(
        self, incoming_frame_data: OnIncomingFramePayloadData
    ) -> None:
        opcode = incoming_frame_data.frame.opcode
        if not opcode.is_data_frame():
            if opcode == Opcode.CLOSE and incoming_frame_data.data:
                self._close_frame_bytes += incoming_frame_data.data
            return
        if opcode == Opcode.TEXT:
            self._exception = WebsocketException(
                "Received invalid data from server, closing websocket connection."
            )
            self.close()
            return
        self.websocketio.write(incoming_frame_data.data)

    def _on_incoming_frame_complete(
        self, incoming_frame_data: OnIncomingFrameCompleteData
    ):
        if (
            incoming_frame_data.frame.opcode == Opcode.CLOSE
            and incoming_frame_data.exception is None
        ):
            if len(self._close_frame_bytes) > 0:
                shutdown_code_as_bytes = self._close_frame_bytes[0:2]
                # The shutdown code is a packed 2 byte unsigned int.
                shutdown_code = struct.unpack(">H", shutdown_code_as_bytes)[0]
                shutdown_reason_in_bytes = self._close_frame_bytes[2:]
                if shutdown_code != 1000:
                    logger.debug("Shutdown code: %s", str(shutdown_code))
                    decoded_shutdown_reason = shutdown_reason_in_bytes.decode(
                        "utf-8"
                    )
                    self._exception = WebsocketException(
                        f"Websocket Closure Reason: {decoded_shutdown_reason}"
                    )
            self.close()

    def _on_send_frame_complete_data(
        self, send_frame_data: OnSendFrameCompleteData
    ) -> None:
        self._send_frame_results_queue.put(send_frame_data)

    def _on_connection_shutdown(self, data: OnConnectionShutdownData) -> None:
        if data.exception:
            self._exception = data.exception
        self.close()


class WebsocketManager:
    def __init__(
        self,
        port,
        max_websocket_connections,
        eice_request_signer,
        user_agent=None,
    ):
        self._port = port
        self._executor = ThreadPoolExecutor(
            max_workers=max_websocket_connections
        )
        self._connection_id_counter = 1
        self._max_websocket_connections = max_websocket_connections
        self._socket = None
        self._inflight_futures_and_websockets = []
        self._eice_request_signer = eice_request_signer
        self._user_agent = user_agent

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.debug("Shutting down WebsocketManager")
        # First set RUNNING flag to false so any remaining loops exit
        self.RUNNING.set()

        # Close all websocket handlers
        for future, web_socket in self._inflight_futures_and_websockets:
            try:
                web_socket.close()
                # Try to cancel any still-running futures
                if not future.done():
                    future.cancel()
            except Exception as e:
                logger.debug(f"Error closing websocket: {str(e)}")

        # Close server socket if exists
        if self._socket:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
                self._socket.close()
            # On Windows, if the socket is already closed, we will get an OSError.
            except OSError:
                pass

        # Shutdown executor with a timeout
        logger.debug("Shutting down executor")
        self._executor.shutdown(wait=False)
        logger.debug("WebsocketManager shutdown complete")

    # Used to break out of while loop in tests.
    RUNNING = threading.Event()

    def run(self):
        # If no port is specified, open a singular websocket connection.
        if not self._port:
            websocketio = (
                WindowsStdinStdoutIO() if is_windows else StdinStdoutIO()
            )
            web_socket = Websocket(websocketio, websocket_id=None)
            try:
                future = self._open_websocket_connection(web_socket)
                # Block until the future completes.
                future.result()
            except WebsocketException as e:
                logger.error(f"Websocket error: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
            finally:
                # Make sure everything is closed and we can exit
                web_socket.close()
                # Force shutdown the executor to ensure the process can exit
                self._executor.shutdown(wait=False)
        else:
            self._listen_on_port()

    def _listen_on_port(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind(("localhost", self._port))
        self._socket.listen()
        print(f"Listening for connections on port {self._port}.")
        while not self.RUNNING.is_set():
            socket_list = [self._socket]
            read_sockets, _, _ = select.select(socket_list, [], [], 0.1)
            if read_sockets:
                conn, addr = self._socket.accept()
                # Check if we have reached max connections
                self._remove_done_futures()
                if (
                    len(self._inflight_futures_and_websockets)
                    >= self._max_websocket_connections
                ):
                    print(
                        f"Max websocket connections {self._max_websocket_connections} have been reached, closing "
                        f"incoming connection."
                    )
                    conn.close()
                    continue

                websocket_id = self._connection_id_counter
                self._connection_id_counter += 1
                print(
                    f"[{websocket_id}] Accepted new tcp connection, opening websocket tunnel."
                )
                try:
                    web_socket = Websocket(TCPSocketIO(conn), websocket_id)
                    future = self._open_websocket_connection(web_socket)
                    future.add_done_callback(
                        self._print_tcp_conn_closed(web_socket)
                    )
                except WebsocketException as e:
                    logger.error(
                        f"[{websocket_id}] Encountered error opening websocket: {e.args}"
                    )

    def _open_websocket_connection(self, web_socket):
        try:
            presigned_url = self._eice_request_signer.get_presigned_url()
            web_socket.connect(presigned_url, self._user_agent)

            # Submit the task with a done callback to clean up resources
            future = self._executor.submit(web_socket.write_data_from_input)

            # Store for cleanup
            self._inflight_futures_and_websockets.append((future, web_socket))

            return future
        except Exception as e:
            logger.error(f"Failed to open websocket connection: {str(e)}")
            web_socket.close()
            raise

    def _print_tcp_conn_closed(self, web_socket):
        def _on_done_callback(future):
            if future.exception():
                logger.error(
                    f"[{web_socket.websocket_id}] Encountered error with websocket: {future.exception().args}"
                )
            print(f"[{web_socket.websocket_id}] Closing tcp connection.")

        return _on_done_callback

    def _remove_done_futures(self):
        self._inflight_futures_and_websockets = [
            (future, web_socket)
            for future, web_socket in self._inflight_futures_and_websockets
            if not future.done()
        ]
