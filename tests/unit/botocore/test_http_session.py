import socket

from mock import patch, Mock, ANY
from tests import unittest
import pytest
from urllib3.exceptions import NewConnectionError, ProtocolError

from botocore.vendored import six
from botocore.awsrequest import AWSRequest
from botocore.awsrequest import AWSHTTPConnectionPool, AWSHTTPSConnectionPool
from botocore.httpsession import get_cert_path
from botocore.httpsession import URLLib3Session, ProxyConfiguration
from botocore.exceptions import ConnectionClosedError, EndpointConnectionError


class TestProxyConfiguration(unittest.TestCase):
    def setUp(self):
        self.url = 'http://localhost/'
        self.auth_url = 'http://user:pass@localhost/'
        self.proxy_config = ProxyConfiguration(
            proxies={'http': 'http://localhost:8081/'}
        )

    def update_http_proxy(self, url):
        self.proxy_config = ProxyConfiguration(
            proxies={'http': url}
        )

    def test_construct_proxy_headers_with_auth(self):
        headers = self.proxy_config.proxy_headers_for(self.auth_url)
        proxy_auth = headers.get('Proxy-Authorization')
        self.assertEqual('Basic dXNlcjpwYXNz', proxy_auth)

    def test_construct_proxy_headers_without_auth(self):
        headers = self.proxy_config.proxy_headers_for(self.url)
        self.assertEqual({}, headers)

    def test_proxy_for_url_no_slashes(self):
        self.update_http_proxy('localhost:8081/')
        proxy_url = self.proxy_config.proxy_url_for(self.url)
        self.assertEqual('http://localhost:8081/', proxy_url)

    def test_proxy_for_url_no_protocol(self):
        self.update_http_proxy('//localhost:8081/')
        proxy_url = self.proxy_config.proxy_url_for(self.url)
        self.assertEqual('http://localhost:8081/', proxy_url)

    def test_fix_proxy_url_has_protocol_http(self):
        proxy_url = self.proxy_config.proxy_url_for(self.url)
        self.assertEqual('http://localhost:8081/', proxy_url)


class TestHttpSessionUtils(unittest.TestCase):
    def test_get_cert_path_path(self):
        path = '/some/path'
        cert_path = get_cert_path(path)
        self.assertEqual(path, cert_path)

    def test_get_cert_path_certifi_or_default(self):
        with patch('botocore.httpsession.where') as where:
            path = '/bundle/path'
            where.return_value = path
            cert_path = get_cert_path(True)
            self.assertEqual(path, cert_path)


class TestURLLib3Session(unittest.TestCase):
    def setUp(self):
        self.request = AWSRequest(
            method='GET',
            url='http://example.com/',
            headers={},
            data=b'',
        )

        self.response = Mock()
        self.response.headers = {}
        self.response.stream.return_value = b''

        self.pool_manager = Mock()
        self.connection = Mock()
        self.connection.urlopen.return_value = self.response
        self.pool_manager.connection_from_url.return_value = self.connection

        self.pool_patch = patch('botocore.httpsession.PoolManager')
        self.proxy_patch = patch('botocore.httpsession.proxy_from_url')
        self.pool_manager_cls = self.pool_patch.start()
        self.proxy_manager_fun = self.proxy_patch.start()
        self.pool_manager_cls.return_value = self.pool_manager
        self.proxy_manager_fun.return_value = self.pool_manager

    def tearDown(self):
        self.pool_patch.stop()
        self.proxy_patch.stop()

    def assert_request_sent(self, headers=None, body=None, url='/', chunked=False):
        if headers is None:
            headers = {}

        self.connection.urlopen.assert_called_once_with(
            method=self.request.method,
            url=url,
            body=body,
            headers=headers,
            retries=ANY,
            assert_same_host=False,
            preload_content=False,
            decode_content=False,
            chunked=chunked,
        )

    def _assert_manager_call(self, manager, *assert_args, **assert_kwargs):
        call_kwargs = {
            'strict': True,
            'maxsize': ANY,
            'timeout': ANY,
            'ssl_context': ANY,
            'socket_options': [],
            'cert_file': None,
            'key_file': None,
        }
        call_kwargs.update(assert_kwargs)
        manager.assert_called_with(*assert_args, **call_kwargs)

    def assert_pool_manager_call(self, *args, **kwargs):
        self._assert_manager_call(self.pool_manager_cls, *args, **kwargs)

    def assert_proxy_manager_call(self, *args, **kwargs):
        self._assert_manager_call(self.proxy_manager_fun, *args, **kwargs)

    def test_forwards_max_pool_size(self):
        URLLib3Session(max_pool_connections=22)
        self.assert_pool_manager_call(maxsize=22)

    def test_forwards_client_cert(self):
        URLLib3Session(client_cert='/some/cert')
        self.assert_pool_manager_call(cert_file='/some/cert', key_file=None)

    def test_forwards_client_cert_and_key_tuple(self):
        cert = ('/some/cert', '/some/key')
        URLLib3Session(client_cert=cert)
        self.assert_pool_manager_call(cert_file=cert[0], key_file=cert[1])

    def test_proxies_config_settings(self):
        proxies = {'http': 'http://proxy.com'}
        proxies_config = {
            'proxy_ca_bundle': 'path/to/bundle',
            'proxy_client_cert': ('path/to/cert', 'path/to/key'),
            'proxy_use_forwarding_for_https': False,
        }
        use_forwarding = proxies_config['proxy_use_forwarding_for_https']
        with patch('botocore.httpsession.create_urllib3_context'):
            session = URLLib3Session(
                proxies=proxies,
                proxies_config=proxies_config
            )
            self.request.url = 'http://example.com/'
            session.send(self.request.prepare())
            self.assert_proxy_manager_call(
                proxies['http'],
                proxy_headers={},
                proxy_ssl_context=ANY,
                use_forwarding_for_https=use_forwarding
            )
        self.assert_request_sent(url=self.request.url)

    def test_proxies_config_settings_unknown_config(self):
        proxies = {'http': 'http://proxy.com'}
        proxies_config = {
            'proxy_ca_bundle': None,
            'proxy_client_cert': None,
            'proxy_use_forwarding_for_https': True,
            'proxy_not_a_real_arg': 'do not pass'
        }
        use_forwarding = proxies_config['proxy_use_forwarding_for_https']
        session = URLLib3Session(
            proxies=proxies,
            proxies_config=proxies_config
        )
        self.request.url = 'http://example.com/'
        session.send(self.request.prepare())
        self.assert_proxy_manager_call(
            proxies['http'],
            proxy_headers={},
            use_forwarding_for_https=use_forwarding
        )
        self.assertNotIn(
            'proxy_not_a_real_arg',
            self.proxy_manager_fun.call_args
        )
        self.assert_request_sent(url=self.request.url)

    def test_http_proxy_scheme_with_http_url(self):
        proxies = {'http': 'http://proxy.com'}
        session = URLLib3Session(proxies=proxies)
        self.request.url = 'http://example.com/'
        session.send(self.request.prepare())
        self.assert_proxy_manager_call(
            proxies['http'],
            proxy_headers={},
        )
        self.assert_request_sent(url=self.request.url)

    def test_http_proxy_scheme_with_https_url(self):
        proxies = {'https': 'http://proxy.com'}
        session = URLLib3Session(proxies=proxies)
        self.request.url = 'https://example.com/'
        session.send(self.request.prepare())
        self.assert_proxy_manager_call(
            proxies['https'],
            proxy_headers={},
        )
        self.assert_request_sent()

    def test_https_proxy_scheme_with_http_url(self):
        proxies = {'http': 'https://proxy.com'}
        session = URLLib3Session(proxies=proxies)
        self.request.url = 'http://example.com/'
        session.send(self.request.prepare())
        self.assert_proxy_manager_call(
            proxies['http'],
            proxy_headers={},
        )
        self.assert_request_sent(url=self.request.url)

    def test_https_proxy_scheme_tls_in_tls(self):
        proxies = {'https': 'https://proxy.com'}
        session = URLLib3Session(proxies=proxies)
        self.request.url = 'https://example.com/'
        session.send(self.request.prepare())
        self.assert_proxy_manager_call(
            proxies['https'],
            proxy_headers={},
        )
        self.assert_request_sent()

    def test_https_proxy_scheme_forwarding_https_url(self):
        proxies = {'https': 'https://proxy.com'}
        proxies_config = {"proxy_use_forwarding_for_https":  True}
        session = URLLib3Session(proxies=proxies, proxies_config=proxies_config)
        self.request.url = 'https://example.com/'
        session.send(self.request.prepare())
        self.assert_proxy_manager_call(
            proxies['https'],
            proxy_headers={},
            use_forwarding_for_https=True,
        )
        self.assert_request_sent(url=self.request.url)

    def test_basic_https_proxy_with_client_cert(self):
        proxies = {'https': 'http://proxy.com'}
        session = URLLib3Session(proxies=proxies, client_cert='/some/cert')
        self.request.url = 'https://example.com/'
        session.send(self.request.prepare())
        self.assert_proxy_manager_call(
            proxies['https'],
            proxy_headers={},
            cert_file='/some/cert',
            key_file=None,
        )
        self.assert_request_sent()

    def test_basic_https_proxy_with_client_cert_and_key(self):
        cert = ('/some/cert', '/some/key')
        proxies = {'https': 'http://proxy.com'}
        session = URLLib3Session(proxies=proxies, client_cert=cert)
        self.request.url = 'https://example.com/'
        session.send(self.request.prepare())
        self.assert_proxy_manager_call(
            proxies['https'],
            proxy_headers={},
            cert_file=cert[0],
            key_file=cert[1],
        )
        self.assert_request_sent()

    def test_urllib3_proxies_kwargs_included(self):
        cert = ('/some/cert', '/some/key')
        proxies = {'https': 'https://proxy.com'}
        proxies_config = {'proxy_client_cert': "path/to/cert"}
        with patch('botocore.httpsession.create_urllib3_context'):
            session = URLLib3Session(
                proxies=proxies, client_cert=cert,
                proxies_config=proxies_config
            )
            self.request.url = 'https://example.com/'
            session.send(self.request.prepare())
            self.assert_proxy_manager_call(
                proxies['https'],
                proxy_headers={},
                cert_file=cert[0],
                key_file=cert[1],
                proxy_ssl_context=ANY
            )
            self.assert_request_sent()

    def test_proxy_ssl_context_uses_check_hostname(self):
        cert = ('/some/cert', '/some/key')
        proxies = {'https': 'https://proxy.com'}
        proxies_config = {'proxy_client_cert': "path/to/cert"}
        with patch('botocore.httpsession.create_urllib3_context'):
            session = URLLib3Session(
                proxies=proxies, client_cert=cert,
                proxies_config=proxies_config
            )
            self.request.url = 'https://example.com/'
            session.send(self.request.prepare())
            last_call = self.proxy_manager_fun.call_args[-1]
            self.assertIs(last_call['ssl_context'].check_hostname, True)

    def test_basic_request(self):
        session = URLLib3Session()
        session.send(self.request.prepare())
        self.assert_request_sent()
        self.response.stream.assert_called_once_with()

    def test_basic_streaming_request(self):
        session = URLLib3Session()
        self.request.stream_output = True
        session.send(self.request.prepare())
        self.assert_request_sent()
        self.response.stream.assert_not_called()

    def test_basic_https_request(self):
        session = URLLib3Session()
        self.request.url = 'https://example.com/'
        session.send(self.request.prepare())
        self.assert_request_sent()

    def test_basic_https_proxy_request(self):
        proxies = {'https': 'http://proxy.com'}
        session = URLLib3Session(proxies=proxies)
        self.request.url = 'https://example.com/'
        session.send(self.request.prepare())
        self.assert_proxy_manager_call(proxies['https'], proxy_headers={})
        self.assert_request_sent()

    def test_basic_proxy_request_caches_manager(self):
        proxies = {'https': 'http://proxy.com'}
        session = URLLib3Session(proxies=proxies)
        self.request.url = 'https://example.com/'
        session.send(self.request.prepare())
        # assert we created the proxy manager
        self.assert_proxy_manager_call(proxies['https'], proxy_headers={})
        session.send(self.request.prepare())
        # assert that we did not create another proxy manager
        self.assertEqual(self.proxy_manager_fun.call_count, 1)

    def test_basic_http_proxy_request(self):
        proxies = {'http': 'http://proxy.com'}
        session = URLLib3Session(proxies=proxies)
        session.send(self.request.prepare())
        self.assert_proxy_manager_call(proxies['http'], proxy_headers={})
        self.assert_request_sent(url=self.request.url)

    def test_ssl_context_is_explicit(self):
        session = URLLib3Session()
        session.send(self.request.prepare())
        _, manager_kwargs = self.pool_manager_cls.call_args
        self.assertIsNotNone(manager_kwargs.get('ssl_context'))

    def test_proxy_request_ssl_context_is_explicit(self):
        proxies = {'http': 'http://proxy.com'}
        session = URLLib3Session(proxies=proxies)
        session.send(self.request.prepare())
        _, proxy_kwargs = self.proxy_manager_fun.call_args
        self.assertIsNotNone(proxy_kwargs.get('ssl_context'))

    def test_session_forwards_socket_options_to_pool_manager(self):
        socket_options = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
        URLLib3Session(socket_options=socket_options)
        self.assert_pool_manager_call(socket_options=socket_options)

    def test_session_forwards_socket_options_to_proxy_manager(self):
        proxies = {'http': 'http://proxy.com'}
        socket_options = [(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)]
        session = URLLib3Session(
            proxies=proxies,
            socket_options=socket_options,
        )
        session.send(self.request.prepare())
        self.assert_proxy_manager_call(
            proxies['http'],
            proxy_headers={},
            socket_options=socket_options,
        )

    def make_request_with_error(self, error):
        self.connection.urlopen.side_effect = error
        session = URLLib3Session()
        session.send(self.request.prepare())

    def test_catches_new_connection_error(self):
        error = NewConnectionError(None, None)
        with pytest.raises(EndpointConnectionError):
           self.make_request_with_error(error)

    def test_catches_bad_status_line(self):
        error = ProtocolError(None)
        with pytest.raises(ConnectionClosedError):
            self.make_request_with_error(error)

    def test_aws_connection_classes_are_used(self):
        session = URLLib3Session()
        # ensure the pool manager is using the correct classes
        http_class = self.pool_manager.pool_classes_by_scheme.get('http')
        self.assertIs(http_class, AWSHTTPConnectionPool)
        https_class = self.pool_manager.pool_classes_by_scheme.get('https')
        self.assertIs(https_class, AWSHTTPSConnectionPool)

    def test_chunked_encoding_is_set_with_header(self):
        session = URLLib3Session()
        self.request.headers['Transfer-Encoding'] = 'chunked'

        session.send(self.request.prepare())
        self.assert_request_sent(
            chunked=True,
            headers={'Transfer-Encoding': 'chunked'},
        )

    def test_chunked_encoding_is_not_set_without_header(self):
        session = URLLib3Session()

        session.send(self.request.prepare())
        self.assert_request_sent(chunked=False)
