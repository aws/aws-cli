import contextlib
import select
import socket
import socketserver
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler

import botocore.session
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ProxyConnectionError,
    ReadTimeoutError,
)
from botocore.vendored.requests import exceptions as requests_exceptions
from tests import mock, unittest


class TestClientHTTPBehavior(unittest.TestCase):
    def setUp(self):
        self.port = unused_port()
        self.localhost = f'http://localhost:{self.port}/'
        self.session = botocore.session.get_session()
        # We need to set fake credentials to ensure credentials aren't searched
        # for which might make additional API calls (assume role, etc).
        self.session.set_credentials('fakeakid', 'fakesecret')

    @unittest.skip('Test has suddenly become extremely flakey.')
    def test_can_proxy_https_request_with_auth(self):
        proxy_url = f'http://user:pass@localhost:{self.port}/'
        config = Config(proxies={'https': proxy_url}, region_name='us-west-1')
        client = self.session.create_client('ec2', config=config)

        class AuthProxyHandler(ProxyHandler):
            event = threading.Event()

            def validate_auth(self):
                proxy_auth = self.headers.get('Proxy-Authorization')
                return proxy_auth == 'Basic dXNlcjpwYXNz'

        try:
            with background(run_server, args=(AuthProxyHandler, self.port)):
                AuthProxyHandler.event.wait(timeout=60)
                client.describe_regions()
        except BackgroundTaskFailed:
            self.fail('Background task did not exit, proxy was not used.')

    @unittest.skip('Proxy cannot connect to service when run in CodeBuild.')
    def test_proxy_request_includes_host_header(self):
        proxy_url = f'http://user:pass@localhost:{self.port}/'
        config = Config(
            proxies={'https': proxy_url},
            proxies_config={'proxy_use_forwarding_for_https': True},
            region_name='us-west-1',
        )
        environ = {'BOTO_EXPERIMENTAL__ADD_PROXY_HOST_HEADER': "True"}
        self.environ_patch = mock.patch('os.environ', environ)
        self.environ_patch.start()
        client = self.session.create_client('ec2', config=config)

        class ConnectProxyHandler(ProxyHandler):
            event = threading.Event()

            def do_CONNECT(self):
                remote_host, remote_port = self.path.split(':')

                # Ensure we're sending the correct host header in CONNECT
                if self.headers.get('host') != remote_host:
                    self.send_response(400)
                    self.end_headers()
                    return

                self.send_response(200)
                self.end_headers()

                remote_host, remote_port = self.path.split(':')
                remote_socket = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM
                )
                remote_socket.connect((remote_host, int(remote_port)))

                self._tunnel(self.request, remote_socket)
                remote_socket.close()

        try:
            with background(run_server, args=(ConnectProxyHandler, self.port)):
                ConnectProxyHandler.event.wait(timeout=60)
                client.describe_regions()
        except BackgroundTaskFailed:
            self.fail('Background task did not exit, proxy was not used.')
        except ProxyConnectionError:
            self.fail('Proxy CONNECT failed, unable to establish connection.')
        except ClientError as e:
            # Fake credentials won't resolve against service
            # but we've successfully contacted through the proxy
            assert e.response['Error']['Code'] == 'AuthFailure'
        finally:
            self.environ_patch.stop()

    def _read_timeout_server(self):
        config = Config(
            read_timeout=0.1,
            retries={'max_attempts': 0},
            region_name='us-weast-2',
        )
        client = self.session.create_client(
            'ec2', endpoint_url=self.localhost, config=config
        )
        client_call_ended_event = threading.Event()

        class FakeEC2(SimpleHandler):
            event = threading.Event()
            msg = b'<response/>'

            def get_length(self):
                return len(self.msg)

            def get_body(self):
                client_call_ended_event.wait(timeout=60)
                return self.msg

        try:
            with background(run_server, args=(FakeEC2, self.port)):
                try:
                    FakeEC2.event.wait(timeout=60)
                    client.describe_regions()
                finally:
                    client_call_ended_event.set()
        except BackgroundTaskFailed:
            self.fail('Fake EC2 service was not called.')

    def test_read_timeout_exception(self):
        with self.assertRaises(ReadTimeoutError):
            self._read_timeout_server()

    def test_old_read_timeout_exception(self):
        with self.assertRaises(requests_exceptions.ReadTimeout):
            self._read_timeout_server()

    @unittest.skip('The current implementation will fail to timeout on linux')
    def test_connect_timeout_exception(self):
        config = Config(
            connect_timeout=0.2,
            retries={'max_attempts': 0},
            region_name='us-weast-2',
        )
        client = self.session.create_client(
            'ec2', endpoint_url=self.localhost, config=config
        )
        server_bound_event = threading.Event()
        client_call_ended_event = threading.Event()

        def no_accept_server():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.port))
            server_bound_event.set()
            client_call_ended_event.wait(timeout=60)
            sock.close()

        with background(no_accept_server):
            server_bound_event.wait(timeout=60)
            with self.assertRaises(ConnectTimeoutError):
                client.describe_regions()
            client_call_ended_event.set()

    def test_invalid_host_gaierror(self):
        config = Config(retries={'max_attempts': 0}, region_name='us-weast-1')
        endpoint = 'https://ec2.us-weast-1.amazonaws.com/'
        client = self.session.create_client(
            'ec2', endpoint_url=endpoint, config=config
        )
        with self.assertRaises(EndpointConnectionError):
            client.describe_regions()

    def test_bad_status_line(self):
        config = Config(retries={'max_attempts': 0}, region_name='us-weast-2')
        client = self.session.create_client(
            'ec2', endpoint_url=self.localhost, config=config
        )

        class BadStatusHandler(BaseHTTPRequestHandler):
            event = threading.Event()

            def do_POST(self):
                self.wfile.write(b'garbage')

        with background(run_server, args=(BadStatusHandler, self.port)):
            with self.assertRaises(ConnectionClosedError):
                BadStatusHandler.event.wait(timeout=60)
                client.describe_regions()


def unused_port():
    with contextlib.closing(socket.socket()) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


class SimpleHandler(BaseHTTPRequestHandler):
    status = 200

    def get_length(self):
        return 0

    def get_body(self):
        return b''

    def do_GET(self):
        length = str(self.get_length())
        self.send_response(self.status)
        self.send_header('Content-Length', length)
        self.end_headers()
        self.wfile.write(self.get_body())

    do_POST = do_PUT = do_GET


class ProxyHandler(BaseHTTPRequestHandler):
    tunnel_chunk_size = 1024
    poll_limit = 10**4

    def _tunnel(self, client, remote):
        client.setblocking(0)
        remote.setblocking(0)
        sockets = [client, remote]
        noop_count = 0
        while True:
            readable, writeable, _ = select.select(sockets, sockets, [], 1)
            if client in readable and remote in writeable:
                noop_count = 0
                client_bytes = client.recv(self.tunnel_chunk_size)
                if not client_bytes:
                    break
                remote.sendall(client_bytes)
            if remote in readable and client in writeable:
                noop_count = 0
                remote_bytes = remote.recv(self.tunnel_chunk_size)
                if not remote_bytes:
                    break
                client.sendall(remote_bytes)

            if noop_count > self.poll_limit:
                # We have a case where all communication has
                # finished but we never saw an empty read.
                # This will leave both sockets as writeable
                # indefinitely. We'll force a break here if
                # we've crossed our polling limit.
                break

            noop_count += 1

    def do_CONNECT(self):
        if not self.validate_auth():
            self.send_response(401)
            self.end_headers()
            return

        self.send_response(200)
        self.end_headers()

        remote_host, remote_port = self.path.split(':')
        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote_socket.connect((remote_host, int(remote_port)))

        self._tunnel(self.request, remote_socket)
        remote_socket.close()

    def validate_auth(self):
        return True


class BackgroundTaskFailed(Exception):
    pass


@contextmanager
def background(target, args=(), timeout=60):
    thread = threading.Thread(target=target, args=args)
    thread.daemon = True
    thread.start()
    try:
        yield target
    finally:
        thread.join(timeout=timeout)
        if thread.is_alive():
            msg = 'Background task did not exit in a timely manner.'
            raise BackgroundTaskFailed(msg)


def run_server(handler, port):
    address = ('', port)
    httpd = socketserver.TCPServer(address, handler, bind_and_activate=False)
    httpd.allow_reuse_address = True
    httpd.server_bind()
    httpd.server_activate()
    handler.event.set()
    httpd.handle_request()
    httpd.server_close()
