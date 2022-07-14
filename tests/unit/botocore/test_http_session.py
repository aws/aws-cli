import socket

import pytest
from urllib3.exceptions import NewConnectionError, ProtocolError, ProxyError

from botocore.awsrequest import (
    AWSHTTPConnectionPool,
    AWSHTTPSConnectionPool,
    AWSRequest,
)
from botocore.exceptions import (
    ConnectionClosedError,
    EndpointConnectionError,
    ProxyConnectionError,
)
from botocore.httpsession import (
    ProxyConfiguration,
    URLLib3Session,
    get_cert_path,
    mask_proxy_url,
)
from tests import mock, unittest


class TestProxyConfiguration(unittest.TestCase):
    def setUp(self):
        self.url = 'http://localhost/'
        self.auth_url = 'http://user:pass@localhost/'
        self.proxy_config = ProxyConfiguration(
            proxies={'http': 'http://localhost:8081/'}
        )

    def update_http_proxy(self, url):
        self.proxy_config = ProxyConfiguration(proxies={'http': url})

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
        with mock.patch('botocore.httpsession.where') as where:
            path = '/bundle/path'
            where.return_value = path
            cert_path = get_cert_path(True)
            self.assertEqual(path, cert_path)


@pytest.mark.parametrize(
    'proxy_url, expected_mask_url',
    (
        ('http://myproxy.amazonaws.com', 'http://myproxy.amazonaws.com'),
        (
            'http://user@myproxy.amazonaws.com',
            'http://***@myproxy.amazonaws.com',
        ),
        (
            'http://user:pass@myproxy.amazonaws.com',
            'http://***:***@myproxy.amazonaws.com',
        ),
        (
            'https://user:pass@myproxy.amazonaws.com',
            'https://***:***@myproxy.amazonaws.com',
        ),
        ('http://user:pass@localhost', 'http://***:***@localhost'),
        ('http://user:pass@localhost:80', 'http://***:***@localhost:80'),
        ('http://user:pass@userpass.com', 'http://***:***@userpass.com'),
        ('http://user:pass@192.168.1.1', 'http://***:***@192.168.1.1'),
        ('http://user:pass@[::1]', 'http://***:***@[::1]'),
        ('http://user:pass@[::1]:80', 'http://***:***@[::1]:80'),
    ),
)
def test_mask_proxy_url(proxy_url, expected_mask_url):
    assert mask_proxy_url(proxy_url) == expected_mask_url


class TestURLLib3Session(unittest.TestCase):
    def setUp(self):
        self.request = AWSRequest(
            method='GET',
            url='http://example.com/',
            headers={},
            data=b'',
        )

        self.response = mock.Mock()
        self.response.headers = {}
        self.response.stream.return_value = b''

        self.pool_manager = mock.Mock()
        self.connection = mock.Mock()
        self.connection.urlopen.return_value = self.response
        self.pool_manager.connection_from_url.return_value = self.connection

        self.pool_patch = mock.patch('botocore.httpsession.PoolManager')
        self.proxy_patch = mock.patch('botocore.httpsession.proxy_from_url')
        self.pool_manager_cls = self.pool_patch.start()
        self.proxy_manager_fun = self.proxy_patch.start()
        self.pool_manager_cls.return_value = self.pool_manager
        self.proxy_manager_fun.return_value = self.pool_manager

    def tearDown(self):
        self.pool_patch.stop()
        self.proxy_patch.stop()

    def assert_request_sent(
        self, headers=None, body=None, url='/', chunked=False
    ):
        if headers is None:
            headers = {}

        self.connection.urlopen.assert_called_once_with(
            method=self.request.method,
            url=url,
            body=body,
            headers=headers,
            retries=mock.ANY,
            assert_same_host=False,
            preload_content=False,
            decode_content=False,
            chunked=chunked,
        )

    def _assert_manager_call(self, manager, *assert_args, **assert_kwargs):
        call_kwargs = {
            'strict': True,
            'maxsize': mock.ANY,
            'timeout': mock.ANY,
            'ssl_context': mock.ANY,
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
        with mock.patch('botocore.httpsession.create_urllib3_context'):
            session = URLLib3Session(
                proxies=proxies, proxies_config=proxies_config
            )
            self.request.url = 'http://example.com/'
            session.send(self.request.prepare())
            self.assert_proxy_manager_call(
                proxies['http'],
                proxy_headers={},
                proxy_ssl_context=mock.ANY,
                use_forwarding_for_https=use_forwarding,
            )
        self.assert_request_sent(url=self.request.url)

    def test_proxies_config_settings_unknown_config(self):
        proxies = {'http': 'http://proxy.com'}
        proxies_config = {
            'proxy_ca_bundle': None,
            'proxy_client_cert': None,
            'proxy_use_forwarding_for_https': True,
            'proxy_not_a_real_arg': 'do not pass',
        }
        use_forwarding = proxies_config['proxy_use_forwarding_for_https']
        session = URLLib3Session(
            proxies=proxies, proxies_config=proxies_config
        )
        self.request.url = 'http://example.com/'
        session.send(self.request.prepare())
        self.assert_proxy_manager_call(
            proxies['http'],
            proxy_headers={},
            use_forwarding_for_https=use_forwarding,
        )
        self.assertNotIn(
            'proxy_not_a_real_arg', self.proxy_manager_fun.call_args
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
        proxies_config = {"proxy_use_forwarding_for_https": True}
        session = URLLib3Session(
            proxies=proxies, proxies_config=proxies_config
        )
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
        with mock.patch('botocore.httpsession.create_urllib3_context'):
            session = URLLib3Session(
                proxies=proxies,
                client_cert=cert,
                proxies_config=proxies_config,
            )
            self.request.url = 'https://example.com/'
            session.send(self.request.prepare())
            self.assert_proxy_manager_call(
                proxies['https'],
                proxy_headers={},
                cert_file=cert[0],
                key_file=cert[1],
                proxy_ssl_context=mock.ANY,
            )
            self.assert_request_sent()

    def test_proxy_ssl_context_uses_check_hostname(self):
        cert = ('/some/cert', '/some/key')
        proxies = {'https': 'https://proxy.com'}
        proxies_config = {'proxy_client_cert': "path/to/cert"}
        with mock.patch('botocore.httpsession.create_urllib3_context'):
            session = URLLib3Session(
                proxies=proxies,
                client_cert=cert,
                proxies_config=proxies_config,
            )
            self.request.url = 'https://example.com/'
            session.send(self.request.prepare())
            last_call = self.proxy_manager_fun.call_args[-1]
            self.assertIs(last_call['ssl_context'].check_hostname, True)

    def test_proxy_ssl_context_does_not_use_check_hostname_if_ip_address(self):
        cert = ('/some/cert', '/some/key')
        proxies_config = {'proxy_client_cert': "path/to/cert"}
        urls = [
            'https://1.2.3.4:5678',
            'https://4.6.0.0',
            'https://[FE80::8939:7684:D84b:a5A4%251]:1234',
            'https://[FE80::8939:7684:D84b:a5A4%251]',
            'https://[FE80::8939:7684:D84b:a5A4]:999',
            'https://[FE80::8939:7684:D84b:a5A4]',
            'https://[::1]:789',
        ]
        for proxy_url in urls:
            with mock.patch('botocore.httpsession.SSLContext'):
                proxies = {'https': proxy_url}
                session = URLLib3Session(
                    proxies=proxies,
                    client_cert=cert,
                    proxies_config=proxies_config,
                )
                self.request.url = 'https://example.com/'
                session.send(self.request.prepare())
                last_call = self.proxy_manager_fun.call_args[-1]
                self.assertIs(last_call['ssl_context'].check_hostname, False)

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

    def test_catches_proxy_error(self):
        self.connection.urlopen.side_effect = ProxyError('test', None)
        session = URLLib3Session(
            proxies={'http': 'http://user:pass@proxy.com'}
        )
        with pytest.raises(ProxyConnectionError) as e:
            session.send(self.request.prepare())
        assert 'user:pass' not in str(e.value)
        assert 'http://***:***@proxy.com' in str(e.value)

    def test_aws_connection_classes_are_used(self):
        session = URLLib3Session()  # noqa
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

    def test_close(self):
        session = URLLib3Session()
        session.close()
        self.pool_manager.clear.assert_called_once_with()

    def test_close_proxied(self):
        proxies = {'https': 'http://proxy.com', 'http': 'http://proxy2.com'}
        session = URLLib3Session(proxies=proxies)
        for proxy, proxy_url in proxies.items():
            self.request.url = '%s://example.com/' % proxy
            session.send(self.request.prepare())

        session.close()
        self.proxy_manager_fun.return_value.clear.assert_called_with()
        # One call for pool manager, one call for each of the proxies
        self.assertEqual(
            self.proxy_manager_fun.return_value.clear.call_count,
            1 + len(proxies),
        )
