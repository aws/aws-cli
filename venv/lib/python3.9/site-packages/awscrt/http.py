"""
HTTP

All network operations in `awscrt.http` are asynchronous.
"""

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import _awscrt
from concurrent.futures import Future
from awscrt import NativeResource
import awscrt.exceptions
from awscrt.io import ClientBootstrap, InputStream, TlsConnectionOptions, SocketOptions
from enum import IntEnum


class HttpVersion(IntEnum):
    """HTTP protocol version enumeration"""
    Unknown = 0  #: Unknown
    Http1_0 = 1  #: HTTP/1.0
    Http1_1 = 2  #: HTTP/1.1
    Http2 = 3  #: HTTP/2


class HttpConnectionBase(NativeResource):
    """Base for HTTP connection classes."""

    __slots__ = ('_shutdown_future', '_version')

    def __init__(self):
        super().__init__()

        self._shutdown_future = Future()

    @property
    def shutdown_future(self):
        """
        concurrent.futures.Future: Completes when this connection has finished shutting down.
        Future will contain a result of None, or an exception indicating why shutdown occurred.
        Note that the connection may have been garbage-collected before this future completes.
        """
        return self._shutdown_future

    @property
    def version(self):
        """HttpVersion: Protocol used by this connection"""
        return self._version

    def close(self):
        """Close the connection.

        Shutdown is asynchronous. This call has no effect if the connection is already
        closing.

        Returns:
            concurrent.futures.Future: This connection's :attr:`shutdown_future`,
            which completes when shutdown has finished.
        """
        _awscrt.http_connection_close(self._binding)
        return self.shutdown_future

    def is_open(self):
        """
        Returns:
            bool: True if this connection is open and usable, False otherwise.
            Check :attr:`shutdown_future` to know when the connection is completely
            finished shutting down.
        """
        return _awscrt.http_connection_is_open(self._binding)


class HttpClientConnection(HttpConnectionBase):
    """
    An HTTP client connection.

    Use :meth:`HttpClientConnection.new()` to establish a new connection.
    """
    __slots__ = ('_host_name', '_port')

    @classmethod
    def new(cls,
            host_name,
            port,
            bootstrap=None,
            socket_options=None,
            tls_connection_options=None,
            proxy_options=None):
        """
        Asynchronously establish a new HttpClientConnection.

        Args:
            host_name (str): Connect to host.

            port (int): Connect to port.

            bootstrap (Optional [ClientBootstrap]): Client bootstrap to use when initiating socket connection.
                If None is provided, the default singleton is used.

            socket_options (Optional[SocketOptions]): Optional socket options.
                If None is provided, then default options are used.

            tls_connection_options (Optional[TlsConnectionOptions]): Optional TLS
                connection options. If None is provided, then the connection will
                be attempted over plain-text.

            proxy_options (Optional[HttpProxyOptions]): Optional proxy options.
                If None is provided then a proxy is not used.

        Returns:
            concurrent.futures.Future: A Future which completes when connection succeeds or fails.
            If successful, the Future will contain a new :class:`HttpClientConnection`.
            Otherwise, it will contain an exception.
        """
        assert isinstance(bootstrap, ClientBootstrap) or bootstrap is None
        assert isinstance(host_name, str)
        assert isinstance(port, int)
        assert isinstance(tls_connection_options, TlsConnectionOptions) or tls_connection_options is None
        assert isinstance(socket_options, SocketOptions) or socket_options is None
        assert isinstance(proxy_options, HttpProxyOptions) or proxy_options is None

        future = Future()
        try:
            if not socket_options:
                socket_options = SocketOptions()

            if not bootstrap:
                bootstrap = ClientBootstrap.get_or_create_static_default()

            connection = cls()
            connection._host_name = host_name
            connection._port = port

            def on_connection_setup(binding, error_code, http_version):
                if error_code == 0:
                    connection._binding = binding
                    connection._version = HttpVersion(http_version)
                    future.set_result(connection)
                else:
                    future.set_exception(awscrt.exceptions.from_code(error_code))

            # on_shutdown MUST NOT reference the connection itself, just the shutdown_future within it.
            # Otherwise we create a circular reference that prevents the connection from getting GC'd.
            shutdown_future = connection.shutdown_future

            def on_shutdown(error_code):
                if error_code:
                    shutdown_future.set_exception(awscrt.exceptions.from_code(error_code))
                else:
                    shutdown_future.set_result(None)

            _awscrt.http_client_connection_new(
                bootstrap,
                on_connection_setup,
                on_shutdown,
                host_name,
                port,
                socket_options,
                tls_connection_options,
                proxy_options)

        except Exception as e:
            future.set_exception(e)

        return future

    @property
    def host_name(self):
        """Remote hostname"""
        return self._host_name

    @property
    def port(self):
        """Remote port"""
        return self._port

    def request(self, request, on_response=None, on_body=None):
        """Create :class:`HttpClientStream` to carry out the request/response exchange.

        NOTE: The HTTP stream sends no data until :meth:`HttpClientStream.activate()`
        is called. Call activate() when you're ready for callbacks and events to fire.

        Args:
            request (HttpRequest): Definition for outgoing request.

            on_response: Optional callback invoked once main response headers are received.
                The function should take the following arguments and return nothing:

                    *   `http_stream` (:class:`HttpClientStream`): HTTP stream carrying
                        out this request/response exchange.

                    *   `status_code` (int): Response status code.

                    *   `headers` (List[Tuple[str, str]]): Response headers as a
                        list of (name,value) pairs.

                    *   `**kwargs` (dict): Forward compatibility kwargs.

                An exception raise by this function will cause the HTTP stream to end in error.
                This callback is always invoked on the connection's event-loop thread.

            on_body: Optional callback invoked 0+ times as response body data is received.
                The function should take the following arguments and return nothing:

                    *   `http_stream` (:class:`HttpClientStream`): HTTP stream carrying
                        out this request/response exchange.

                    *   `chunk` (buffer): Response body data (not necessarily
                        a whole "chunk" of chunked encoding).

                    *   `**kwargs` (dict): Forward-compatibility kwargs.

                An exception raise by this function will cause the HTTP stream to end in error.
                This callback is always invoked on the connection's event-loop thread.

        Returns:
            HttpClientStream:
        """
        return HttpClientStream(self, request, on_response, on_body)


class HttpStreamBase(NativeResource):
    """Base for HTTP stream classes"""
    __slots__ = ('_connection', '_completion_future', '_on_body_cb')

    def __init__(self, connection, on_body=None):
        super().__init__()
        self._connection = connection
        self._completion_future = Future()
        self._on_body_cb = on_body

    @property
    def connection(self):
        return self._connection

    @property
    def completion_future(self):
        return self._completion_future

    def _on_body(self, chunk):
        if self._on_body_cb:
            self._on_body_cb(http_stream=self, chunk=chunk)


class HttpClientStream(HttpStreamBase):
    """HTTP stream that sends a request and receives a response.

    Create an HttpClientStream with :meth:`HttpClientConnection.request()`.

    NOTE: The HTTP stream sends no data until :meth:`HttpClientStream.activate()`
    is called. Call activate() when you're ready for callbacks and events to fire.

    Attributes:
        connection (HttpClientConnection): This stream's connection.

        completion_future (concurrent.futures.Future): Future that will contain
            the response status code (int) when the request/response exchange
            completes. If the exchange fails to complete, the Future will
            contain an exception indicating why it failed.
    """
    __slots__ = ('_response_status_code', '_on_response_cb', '_on_body_cb', '_request')

    def __init__(self, connection, request, on_response=None, on_body=None):
        assert isinstance(connection, HttpClientConnection)
        assert isinstance(request, HttpRequest)
        assert callable(on_response) or on_response is None
        assert callable(on_body) or on_body is None

        super().__init__(connection, on_body)

        self._on_response_cb = on_response
        self._response_status_code = None

        # keep HttpRequest alive until stream completes
        self._request = request

        self._binding = _awscrt.http_client_stream_new(self, connection, request)

    @property
    def response_status_code(self):
        """int: The response status code.

        This is None until a response arrives."""
        return self._response_status_code

    def activate(self):
        """Begin sending the request.

        The HTTP stream does nothing until this is called. Call activate() when you
        are ready for its callbacks and events to fire.
        """
        _awscrt.http_client_stream_activate(self)

    def _on_response(self, status_code, name_value_pairs):
        self._response_status_code = status_code

        if self._on_response_cb:
            self._on_response_cb(http_stream=self, status_code=status_code, headers=name_value_pairs)

    def _on_complete(self, error_code):
        # done with HttpRequest, drop reference
        self._request = None

        if error_code == 0:
            self._completion_future.set_result(self._response_status_code)
        else:
            self._completion_future.set_exception(awscrt.exceptions.from_code(error_code))


class HttpMessageBase(NativeResource):
    """
    Base for HttpRequest and HttpResponse classes.
    """
    __slots__ = ('_headers', '_body_stream')

    def __init__(self, binding, headers, body_stream=None):
        assert isinstance(headers, HttpHeaders)

        super().__init__()
        self._binding = binding
        self._headers = headers
        self._body_stream = None

        if body_stream:
            self.body_stream = body_stream

    @property
    def headers(self):
        """HttpHeaders: Headers to send."""
        return self._headers

    @property
    def body_stream(self):
        return self._body_stream

    @body_stream.setter
    def body_stream(self, stream):
        self._body_stream = InputStream.wrap(stream)
        _awscrt.http_message_set_body_stream(self._binding, self._body_stream)


class HttpRequest(HttpMessageBase):
    """
    Definition for an outgoing HTTP request.

    The request may be transformed (ex: signing the request) before its data is eventually sent.

    Args:
        method (str): HTTP request method (verb). Default value is "GET".
        path (str): HTTP path-and-query value. Default value is "/".
        headers (Optional[HttpHeaders]): Optional headers. If None specified,
            an empty :class:`HttpHeaders` is created.
        body_stream(Optional[Union[InputStream, io.IOBase]]): Optional body as binary stream.
    """

    __slots__ = ()

    def __init__(self, method='GET', path='/', headers=None, body_stream=None):
        assert isinstance(headers, HttpHeaders) or headers is None

        if headers is None:
            headers = HttpHeaders()

        binding = _awscrt.http_message_new_request(headers)
        super().__init__(binding, headers, body_stream)
        self.method = method
        self.path = path

    @classmethod
    def _from_bindings(cls, request_binding, headers_binding):
        """Construct HttpRequest and its HttpHeaders from pre-existing native objects"""

        # avoid class's default constructor
        # just invoke parent class's __init__()
        request = cls.__new__(cls)
        headers = HttpHeaders._from_binding(headers_binding)
        super(cls, request).__init__(request_binding, headers)
        return request

    @property
    def method(self):
        """str: HTTP request method (verb)."""
        return _awscrt.http_message_get_request_method(self._binding)

    @method.setter
    def method(self, method):
        _awscrt.http_message_set_request_method(self._binding, method)

    @property
    def path(self):
        """str: HTTP path-and-query value."""
        return _awscrt.http_message_get_request_path(self._binding)

    @path.setter
    def path(self, path):
        return _awscrt.http_message_set_request_path(self._binding, path)


class HttpHeaders(NativeResource):
    """
    Collection of HTTP headers.

    A given header name may have multiple values.
    Header names are always treated in a case-insensitive manner.
    HttpHeaders can be iterated over as (name,value) pairs.

    Args:
        name_value_pairs (Optional[List[Tuple[str, str]]]): Construct from a
            collection of (name,value) pairs.
    """

    __slots__ = ()

    def __init__(self, name_value_pairs=None):
        super().__init__()
        self._binding = _awscrt.http_headers_new()
        if name_value_pairs:
            self.add_pairs(name_value_pairs)

    @classmethod
    def _from_binding(cls, binding):
        """Construct from a pre-existing native object"""
        headers = cls.__new__(cls)  # avoid class's default constructor
        super(cls, headers).__init__()  # just invoke parent class's __init__()
        headers._binding = binding
        return headers

    def add(self, name, value):
        """
        Add a name-value pair.

        Args:
            name (str): Name.
            value (str): Value.
        """
        assert isinstance(name, str)
        assert isinstance(value, str)
        _awscrt.http_headers_add(self._binding, name, value)

    def add_pairs(self, name_value_pairs):
        """
        Add list of (name,value) pairs.

        Args:
            name_value_pairs (List[Tuple[str, str]]): List of (name,value) pairs.
        """
        _awscrt.http_headers_add_pairs(self._binding, name_value_pairs)

    def set(self, name, value):
        """
        Set a name-value pair, any existing values for the name are removed.

        Args:
            name (str): Name.
            value (str): Value.
        """
        assert isinstance(name, str)
        assert isinstance(value, str)
        _awscrt.http_headers_set(self._binding, name, value)

    def get_values(self, name):
        """
        Return an iterator over the values for this name.

        Args:
            name (str): Name.

        Returns:
            Iterator[Tuple[str, str]]:
        """
        assert isinstance(name, str)
        name = name.lower()
        for i in range(_awscrt.http_headers_count(self._binding)):
            name_i, value_i = _awscrt.http_headers_get_index(self._binding, i)
            if name_i.lower() == name:
                yield value_i

    def get(self, name, default=None):
        """
        Get the first value for this name, ignoring any additional values.
        Returns `default` if no values exist.

        Args:
            name (str): Name.
            default (Optional[str]): If `name` not found, this value is returned.
                Defaults to None.
        Returns:
            str:
        """
        assert isinstance(name, str)
        return _awscrt.http_headers_get(self._binding, name, default)

    def remove(self, name):
        """
        Remove all values for this name.
        Raises a KeyError if name not found.

        Args:
            name (str): Header name.
        """
        assert isinstance(name, str)
        _awscrt.http_headers_remove(self._binding, name)

    def remove_value(self, name, value):
        """
        Remove a specific value for this name.
        Raises a ValueError if value not found.

        Args:
            name (str): Name.
            value (str): Value.
        """
        assert isinstance(name, str)
        assert isinstance(value, str)
        _awscrt.http_headers_remove_value(self._binding, name, value)

    def clear(self):
        """
        Clear all headers.
        """
        _awscrt.http_headers_clear(self._binding)

    def __iter__(self):
        """
        Iterate over all (name,value) pairs.
        """
        for i in range(_awscrt.http_headers_count(self._binding)):
            yield _awscrt.http_headers_get_index(self._binding, i)

    def __str__(self):
        return self.__class__.__name__ + "(" + str([pair for pair in self]) + ")"


class HttpProxyConnectionType(IntEnum):
    """Proxy connection type enumeration"""
    Legacy = 0
    """
    Use the old connection establishment logic that would use:

         1. Forwarding if not using TLS
         2. Tunneling if using TLS
    """

    Forwarding = 1
    """
    Establish a request forwarding connection to the proxy.

    In this case, TLS is not a valid option.
    """

    Tunneling = 2
    """Establish a tunneling connection through the proxy to the ultimate endpoint."""


class HttpProxyAuthenticationType(IntEnum):
    """Proxy authentication type enumeration."""
    Nothing = 0
    """No authentication"""

    Basic = 1
    """Username and password"""


class HttpProxyOptions:
    """
    Proxy options for HTTP clients.

    Args:
        host_name (str): Name of the proxy server to connect through.

        port (int): Port number of the proxy server to connect through.

        tls_connection_options (Optional[TlsConnectionOptions]): Optional
            `TlsConnectionOptions` for the Local to Proxy connection.
            Must be distinct from the `TlsConnectionOptions`
            provided to the HTTP connection.

        auth_type (HttpProxyAuthenticationType): Type of proxy authentication to use.
            Default is :const:`HttpProxyAuthenticationType.Nothing`.

        auth_username (Optional[str]): Username to use when `auth_type` is
            :const:`HttpProxyAuthenticationType.Basic`.

        auth_password (Optional[str]): Username to use when `auth_type` is
            :const:`HttpProxyAuthenticationType.Basic`.

        connection_type (Optional[HttpProxyConnectionType): Type of proxy connection to make.
            Default is :const:`HttpProxyConnectionType.Legacy`.


    Attributes:
        host_name (str): Name of the proxy server to connect through.

        port (int): Port number of the proxy server to connect through.

        tls_connection_options (Optional[TlsConnectionOptions]): Optional
            `TlsConnectionOptions` for the Local to Proxy connection.
            Must be distinct from the `TlsConnectionOptions`
            provided to the HTTP connection.

        auth_type (HttpProxyAuthenticationType): Type of proxy authentication to use.

        auth_username (Optional[str]): Username to use when `auth_type` is
            :const:`HttpProxyAuthenticationType.Basic`.

        auth_password (Optional[str]): Username to use when `auth_type` is
            :const:`HttpProxyAuthenticationType.Basic`.

        connection_type (HttpProxyConnectionType): Type of proxy connection to make.

    """

    def __init__(self,
                 host_name,
                 port,
                 tls_connection_options=None,
                 auth_type=HttpProxyAuthenticationType.Nothing,
                 auth_username=None,
                 auth_password=None,
                 connection_type=HttpProxyConnectionType.Legacy):
        self.host_name = host_name
        self.port = port
        self.tls_connection_options = tls_connection_options
        self.auth_type = auth_type
        self.auth_username = auth_username
        self.auth_password = auth_password
        self.connection_type = connection_type
