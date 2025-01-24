"""
I/O library for `awscrt`.

All networking in `awscrt` is asynchronous.
Long-running event-loop threads are used for concurrency.
"""

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import _awscrt
from awscrt import NativeResource
from enum import IntEnum
import threading
from typing import Union


class LogLevel(IntEnum):
    NoLogs = 0  #:
    Fatal = 1  #:
    Error = 2  #:
    Warn = 3  #:
    Info = 4  #:
    Debug = 5  #:
    Trace = 6  #:


def init_logging(log_level, file_name):
    """Initialize logging in `awscrt`.

    Args:
        log_level (LogLevel): Display messages of this importance and higher.
            `LogLevel.NoLogs` will disable logging.
        file_name (str): Logging destination. To write to stdout or stderr pass
            'stdout' or 'stderr' as strings. Otherwise, a file path is assumed.
    """
    assert log_level is not None
    assert file_name is not None

    _awscrt.init_logging(log_level, file_name)


class EventLoopGroup(NativeResource):
    """A collection of event-loops.

    An event-loop is a thread for doing async work, such as I/O. Classes that
    need to do async work will ask the EventLoopGroup for an event-loop to use.

    Args:
        num_threads (Optional[int]): Maximum number of event-loops to create.
            If unspecified, one is created for each processor on the machine.

        cpu_group (Optional[int]): Optional processor group to which all
            threads will be pinned. Useful for systems with non-uniform
            memory access (NUMA) nodes. If specified, the number of threads
            will be capped at the number of processors in the group.

    Attributes:
        shutdown_event (threading.Event): Signals when EventLoopGroup's threads
            have all finished shutting down. Shutdown begins when the
            EventLoopGroup object is destroyed.
    """

    _static_event_loop_group = None
    _static_event_loop_group_lock = threading.Lock()
    __slots__ = ('shutdown_event')

    def __init__(self, num_threads=None, cpu_group=None):
        super().__init__()

        if num_threads is None:
            # C uses 0 to indicate defaults
            num_threads = 0

        if cpu_group is None:
            is_pinned = False
            cpu_group = 0
        else:
            is_pinned = True

        shutdown_event = threading.Event()

        def on_shutdown():
            shutdown_event.set()

        self.shutdown_event = shutdown_event
        self._binding = _awscrt.event_loop_group_new(num_threads, is_pinned, cpu_group, on_shutdown)

    @staticmethod
    def get_or_create_static_default():
        with EventLoopGroup._static_event_loop_group_lock:
            if EventLoopGroup._static_event_loop_group is None:
                EventLoopGroup._static_event_loop_group = EventLoopGroup()
            return EventLoopGroup._static_event_loop_group

    @staticmethod
    def release_static_default():
        with EventLoopGroup._static_event_loop_group_lock:
            EventLoopGroup._static_event_loop_group = None


class HostResolverBase(NativeResource):
    """DNS host resolver."""
    __slots__ = ()


class DefaultHostResolver(HostResolverBase):
    """Default DNS host resolver.

    Args:
        event_loop_group (EventLoopGroup): EventLoopGroup to use.
        max_hosts(int): Max host names to cache.
    """

    _static_host_resolver = None
    _static_host_resolver_lock = threading.Lock()
    __slots__ = ()

    def __init__(self, event_loop_group, max_hosts=16):
        assert isinstance(event_loop_group, EventLoopGroup)

        super().__init__()
        self._binding = _awscrt.host_resolver_new_default(max_hosts, event_loop_group)

    @staticmethod
    def get_or_create_static_default():
        with DefaultHostResolver._static_host_resolver_lock:
            if DefaultHostResolver._static_host_resolver is None:
                DefaultHostResolver._static_host_resolver = DefaultHostResolver(
                    EventLoopGroup.get_or_create_static_default())
            return DefaultHostResolver._static_host_resolver

    @staticmethod
    def release_static_default():
        with DefaultHostResolver._static_host_resolver_lock:
            DefaultHostResolver._static_host_resolver = None


class ClientBootstrap(NativeResource):
    """Handles creation and setup of client socket connections.

    Args:
        event_loop_group (EventLoopGroup): EventLoopGroup to use.
        host_resolver (HostResolverBase): DNS host resolver to use.

    Attributes:
        shutdown_event (threading.Event): Signals when the ClientBootstrap's
            internal resources finish shutting down.
            Shutdown begins when the ClientBootstrap object is destroyed.
    """

    _static_client_bootstrap = None
    _static_client_bootstrap_lock = threading.Lock()
    __slots__ = ('shutdown_event')

    def __init__(self, event_loop_group, host_resolver):
        assert isinstance(event_loop_group, EventLoopGroup)
        assert isinstance(host_resolver, HostResolverBase)

        super().__init__()

        shutdown_event = threading.Event()

        def on_shutdown():
            shutdown_event.set()

        self.shutdown_event = shutdown_event
        self._binding = _awscrt.client_bootstrap_new(event_loop_group, host_resolver, on_shutdown)

    @staticmethod
    def get_or_create_static_default():
        with ClientBootstrap._static_client_bootstrap_lock:
            if ClientBootstrap._static_client_bootstrap is None:
                ClientBootstrap._static_client_bootstrap = ClientBootstrap(
                    EventLoopGroup.get_or_create_static_default(),
                    DefaultHostResolver.get_or_create_static_default())
            return ClientBootstrap._static_client_bootstrap

    @staticmethod
    def release_static_default():
        with ClientBootstrap._static_client_bootstrap_lock:
            ClientBootstrap._static_client_bootstrap = None


def _read_binary_file(filepath):
    with open(filepath, mode='rb') as fh:
        contents = fh.read()
    return contents


class SocketDomain(IntEnum):
    IPv4 = 0  #:
    IPv6 = 1  #:
    Local = 2  #: Unix domain sockets (at at least something like them)


class SocketType(IntEnum):
    Stream = 0
    """A streaming socket sends reliable messages over a two-way connection.
    This means TCP when used with `SocketDomain.IPv4/6`,
    and Unix domain sockets when used with `SocketDomain.Local`"""

    DGram = 1
    """A datagram socket is connectionless and sends unreliable messages.
    This means UDP when used with `SocketDomain.IPv4/6`.
    `SocketDomain.Local` is not compatible with `DGram` """


class SocketOptions:
    """Socket options.

    Attributes:
        domain (SocketDomain): Socket domain.
        type (SocketType): Socket type.
        connect_timeout_ms (int): Connection timeout, in milliseconds.
        keep_alive (bool): If set True, periodically transmit keepalive messages
            for detecting a disconnected peer.
        keep_alive_timeout_secs (int): Duration, in seconds, between keepalive
            transmissions in idle condition. If 0, then a default value is used.
        keep_alive_interval_secs (int): Duration, in seconds, between keepalive
            retransmissions, if acknowledgement of previous keepalive transmission
            is not received. If 0, then a default value is used.
        keep_alive_max_probes (int): If set, sets the number of keepalive probes
            allowed to fail before a connection is considered lost.
    """

    __slots__ = (
        'domain', 'type', 'connect_timeout_ms', 'keep_alive',
        'keep_alive_timeout_secs', 'keep_alive_interval_secs', 'keep_alive_max_probes'
    )

    def __init__(self):
        for slot in self.__slots__:
            setattr(self, slot, None)

        self.domain = SocketDomain.IPv6
        self.type = SocketType.Stream
        self.connect_timeout_ms = 5000
        self.keep_alive = False
        self.keep_alive_interval_secs = 0
        self.keep_alive_timeout_secs = 0
        self.keep_alive_max_probes = 0


class TlsVersion(IntEnum):
    SSLv3 = 0  #:
    TLSv1 = 1  #:
    TLSv1_1 = 2  #:
    TLSv1_2 = 3  #:
    TLSv1_3 = 4  #:
    DEFAULT = 128  #:


class TlsCipherPref(IntEnum):
    """TLS Cipher Preference.

       Each TlsCipherPref represents an ordered list of TLS Ciphers to use when negotiating a TLS Connection. At
       present, the ability to configure arbitrary orderings of TLS Ciphers is not allowed, and only a curated list of
       vetted TlsCipherPref's are exposed."""

    DEFAULT = 0
    """The underlying platform's default TLS Cipher Preference ordering. This is usually the best option, as it will be
       automatically updated as the underlying OS or platform changes, and will always be supported on all platforms."""

    PQ_TLSv1_0_2021_05 = 6  #:
    """A TLS Cipher Preference ordering that supports TLS 1.0 through TLS 1.3, and has Kyber Round 3 as its highest
       priority post-quantum key exchange algorithm. PQ algorithms in this preference list will always be used in hybrid
       mode, and will be combined with a classical ECDHE key exchange that is performed in addition to the PQ key
       exchange. This preference makes a best-effort to negotiate a PQ algorithm, but if the peer does not support any
       PQ algorithms the TLS connection will fall back to a single classical algorithm for key exchange (such as ECDHE
       or RSA).

       NIST has announced that they plan to eventually standardize Kyber. However, the NIST standardization process might
       introduce minor changes that could cause the final Kyber standard to differ from the Kyber Round 3 implementation
       available in this preference list."""

    def is_supported(self):
        """Return whether this Cipher Preference is available in the underlying platform's TLS implementation"""
        return _awscrt.is_tls_cipher_supported(self.value)


class TlsContextOptions:
    """Options to create a TLS context.

    The static `TlsContextOptions.create_X()` methods provide common TLS configurations.
    A default-initialized TlsContextOptions has `verify_peer` set True.

    Attributes:
        min_tls_ver (TlsVersion): Minimum TLS version to use.
            System defaults are used by default.
        cipher_pref (TlsCipherPref): The TLS Cipher Preference to use. System defaults are used by default.
        verify_peer (bool): Whether to validate the peer's x.509 certificate.
        alpn_list (Optional[List[str]]): If set, names to use in Application Layer
            Protocol Negotiation (ALPN). ALPN is not supported on all systems,
            see :meth:`is_alpn_available()`. This can be customized per connection,
            via :meth:`TlsConnectionOptions.set_alpn_list()`.
    """
    __slots__ = (
        'min_tls_ver',
        'ca_dirpath',
        'ca_buffer',
        'cipher_pref',
        'alpn_list',
        'certificate_buffer',
        'private_key_buffer',
        'pkcs12_filepath',
        'pkcs12_password',
        'verify_peer',
        '_pkcs11_lib',
        '_pkcs11_user_pin',
        '_pkcs11_slot_id',
        '_pkcs11_token_label',
        '_pkcs11_private_key_label',
        '_pkcs11_cert_file_path',
        '_pkcs11_cert_file_contents',
        '_windows_cert_store_path',
    )

    def __init__(self):

        for slot in self.__slots__:
            setattr(self, slot, None)

        self.min_tls_ver = TlsVersion.DEFAULT
        self.cipher_pref = TlsCipherPref.DEFAULT
        self.verify_peer = True

    @staticmethod
    def create_client_with_mtls_from_path(cert_filepath, pk_filepath):
        """
        Create options configured for use with mutual TLS in client mode.

        Both files are treated as PKCS #7 PEM armored.
        They are loaded from disk and stored in buffers internally.

        Args:
            cert_filepath (str): Path to certificate file.
            pk_filepath (str): Path to private key file.

        Returns:
            TlsContextOptions:
        """

        assert isinstance(cert_filepath, str)
        assert isinstance(pk_filepath, str)

        cert_buffer = _read_binary_file(cert_filepath)
        key_buffer = _read_binary_file(pk_filepath)

        return TlsContextOptions.create_client_with_mtls(cert_buffer, key_buffer)

    @staticmethod
    def create_client_with_mtls(cert_buffer, key_buffer):
        """
        Create options configured for use with mutual TLS in client mode.

        Both buffers are treated as PKCS #7 PEM armored.

        Args:
            cert_buffer (bytes): Certificate contents
            key_buffer (bytes): Private key contents.

        Returns:
            TlsContextOptions:
        """
        assert isinstance(cert_buffer, bytes)
        assert isinstance(key_buffer, bytes)

        opt = TlsContextOptions()
        opt.certificate_buffer = cert_buffer
        opt.private_key_buffer = key_buffer

        return opt

    @staticmethod
    def create_client_with_mtls_pkcs11(*,
                                       pkcs11_lib: 'Pkcs11Lib',
                                       user_pin: Union[str, None],
                                       slot_id: int = None,
                                       token_label: str = None,
                                       private_key_label: str = None,
                                       cert_file_path: str = None,
                                       cert_file_contents=None):
        """
        Create options configured for use with mutual TLS in client mode,
        using a PKCS#11 library for private key operations.

        NOTE: This configuration only works on Unix devices.

        Keyword Args:
            pkcs11_lib (Pkcs11Lib): Use this PKCS#11 library

            user_pin (str): User PIN, for logging into the PKCS#11 token.
                Pass `None` to log into a token with a "protected authentication path".

            slot_id (Optional[int]): ID of slot containing PKCS#11 token.
                If not specified, the token will be chosen based on other criteria (such as token label).

            token_label (Optional[str]): Label of the PKCS#11 token to use.
                If not specified, the token will be chosen based on other criteria (such as slot ID).

            private_key_label (Optional[str]): Label of private key object on PKCS#11 token.
                If not specified, the key will be chosen based on other criteria
                (such as being the only available private key on the token).

            cert_file_path (Optional[str]): Use this X.509 certificate (path to file on disk).
                The certificate must be PEM-formatted. The certificate may be
                specified by other means instead (ex: `cert_file_contents`)

            cert_file_contents (Optional[Union[str, bytes, bytearray]]):
                Use this X.509 certificate (contents in memory).
                The certificate must be PEM-formatted. The certificate may be
                specified by other means instead (ex: `cert_file_path`)
        """

        assert isinstance(pkcs11_lib, Pkcs11Lib)
        assert isinstance(user_pin, str) or user_pin is None
        assert isinstance(slot_id, int) or slot_id is None
        assert isinstance(token_label, str) or token_label is None
        assert isinstance(private_key_label, str) or private_key_label is None
        assert isinstance(cert_file_path, str) or cert_file_path is None
        # note: not validating cert_file_contents, because "bytes-like object" isn't a strict type

        opt = TlsContextOptions()
        opt._pkcs11_lib = pkcs11_lib
        opt._pkcs11_user_pin = user_pin
        opt._pkcs11_slot_id = slot_id
        opt._pkcs11_token_label = token_label
        opt._pkcs11_private_key_label = private_key_label
        opt._pkcs11_cert_file_path = cert_file_path
        opt._pkcs11_cert_file_contents = cert_file_contents
        return opt

    @staticmethod
    def create_client_with_mtls_pkcs12(pkcs12_filepath, pkcs12_password):
        """
        Create options configured for use with mutual TLS in client mode.

        NOTE: This configuration only works on Apple devices.

        Args:
            pkcs12_filepath (str): Path to PKCS #12 file.
                The file is loaded from disk and stored internally.
            pkcs12_password (str): Password to PKCS #12 file.

        Returns:
            TlsContextOptions:
        """

        assert isinstance(pkcs12_filepath, str)
        assert isinstance(pkcs12_password, str)

        opt = TlsContextOptions()
        opt.pkcs12_filepath = pkcs12_filepath
        opt.pkcs12_password = pkcs12_password
        return opt

    @staticmethod
    def create_client_with_mtls_windows_cert_store_path(cert_path):
        """
        Create options configured for use with mutual TLS in client mode,
        using a certificate in a Windows certificate store.

        NOTE: This configuration only works on Windows devices.

        Args:
            cert_path (str): Path to certificate in a Windows certificate store.
                The path must use backslashes and end with the certificate's thumbprint.
                Example: ``CurrentUser\\MY\\A11F8A9B5DF5B98BA3508FBCA575D09570E0D2C6``

        Returns:
            TlsContextOptions
        """
        assert isinstance(cert_path, str)
        opt = TlsContextOptions()
        opt._windows_cert_store_path = cert_path
        return opt

    @staticmethod
    def create_server_from_path(cert_filepath, pk_filepath):
        """
        Create options configured for use in server mode.

        Both files are treated as PKCS #7 PEM armored.
        They are loaded from disk and stored in buffers internally.

        Args:
            cert_filepath (str): Path to certificate file.
            pk_filepath (str): Path to private key file.

        Returns:
            TlsContextOptions:
        """

        assert isinstance(cert_filepath, str)
        assert isinstance(pk_filepath, str)

        cert_buffer = _read_binary_file(cert_filepath)
        key_buffer = _read_binary_file(pk_filepath)

        return TlsContextOptions.create_server(cert_buffer, key_buffer)

    @staticmethod
    def create_server(cert_buffer, key_buffer):
        """
        Create options configured for use in server mode.

        Both buffers are treated as PKCS #7 PEM armored.

        Args:
            cert_buffer (bytes): Certificate contents.
            key_buffer (bytes): Private key contents.

        Returns:
            TlsContextOptions:
        """
        assert isinstance(cert_buffer, bytes)
        assert isinstance(key_buffer, bytes)

        opt = TlsContextOptions()
        opt.certificate_buffer = cert_buffer
        opt.private_key_buffer = key_buffer
        opt.verify_peer = False
        return opt

    @staticmethod
    def create_server_pkcs12(pkcs12_filepath, pkcs12_password):
        """
        Create options configured for use in server mode.

        NOTE: This configuration only works on Apple devices.

        Args:
            pkcs12_filepath (str): Path to PKCS #12 file.
            pkcs12_password (str): Password to PKCS #12 file.

        Returns:
            TlsContextOptions:
        """

        assert isinstance(pkcs12_filepath, str)
        assert isinstance(pkcs12_password, str)

        opt = TlsContextOptions()
        opt.pkcs12_filepath = pkcs12_filepath
        opt.pkcs12_password = pkcs12_password
        opt.verify_peer = False
        return opt

    def override_default_trust_store_from_path(self, ca_dirpath=None, ca_filepath=None):
        """Override default trust store.

        Args:
            ca_dirpath (Optional[str]): Path to directory containing
                trusted certificates, which will overrides the default trust store.
                Only supported on Unix.
            ca_filepath(Optional[str]): Path to file containing PEM armored chain
                of trusted CA certificates.
        """

        assert isinstance(ca_dirpath, str) or ca_dirpath is None
        assert isinstance(ca_filepath, str) or ca_filepath is None

        if ca_filepath:
            ca_buffer = _read_binary_file(ca_filepath)
            self.override_default_trust_store(ca_buffer)

        self.ca_dirpath = ca_dirpath

    def override_default_trust_store(self, rootca_buffer):
        """Override default trust store.

        Args:
            rootca_buffer (bytes): PEM armored chain of trusted CA certificates.
        """
        assert isinstance(rootca_buffer, bytes)

        self.ca_buffer = rootca_buffer


class ClientTlsContext(NativeResource):
    """Client TLS context.

    A context is expensive, but can be used for the lifetime of the application
    by all outgoing connections that wish to use the same TLS configuration.

    Args:
        options (TlsContextOptions): Configuration options.
    """
    __slots__ = ()

    def __init__(self, options):
        assert isinstance(options, TlsContextOptions)

        super().__init__()
        self._binding = _awscrt.client_tls_ctx_new(
            options.min_tls_ver.value,
            options.cipher_pref.value,
            options.ca_dirpath,
            options.ca_buffer,
            _alpn_list_to_str(options.alpn_list),
            options.certificate_buffer,
            options.private_key_buffer,
            options.pkcs12_filepath,
            options.pkcs12_password,
            options.verify_peer,
            options._pkcs11_lib,
            options._pkcs11_user_pin,
            options._pkcs11_slot_id,
            options._pkcs11_token_label,
            options._pkcs11_private_key_label,
            options._pkcs11_cert_file_path,
            options._pkcs11_cert_file_contents,
            options._windows_cert_store_path,
        )

    def new_connection_options(self):
        """Create a :class:`TlsConnectionOptions` that makes use of this TLS context.

        Returns:
                TlsConnectionOptions:
        """
        return TlsConnectionOptions(self)


class TlsConnectionOptions(NativeResource):
    """Connection-specific TLS options.

    Note that, while a TLS context is an expensive object, a :class:`TlsConnectionOptions` is cheap.

    Args:
        tls_ctx (ClientTlsContext): TLS context. A context can be shared by many connections.

    Attributes:
        tls_ctx (ClientTlsContext): TLS context.
    """
    __slots__ = ('tls_ctx')

    def __init__(self, tls_ctx):
        assert isinstance(tls_ctx, ClientTlsContext)

        super().__init__()
        self.tls_ctx = tls_ctx
        self._binding = _awscrt.tls_connections_options_new_from_ctx(tls_ctx)

    def set_alpn_list(self, alpn_list):
        """Set names to use in Application Layer Protocol Negotiation (ALPN).

        This overrides any ALPN list on the TLS context, see :attr:`TlsContextOptions.alpn_list`.
        ALPN is not supported on all systems, see :meth:`is_alpn_available()`.

        Args:
            alpn_list (List[str]): List of protocol names.
        """
        _awscrt.tls_connection_options_set_alpn_list(self, _alpn_list_to_str(alpn_list))

    def set_server_name(self, server_name):
        """Set server name.

        Sets name for TLS Server Name Indication (SNI).
        Name is also used for x.509 validation.

        Args:
            server_name (str): Server name.
        """
        _awscrt.tls_connection_options_set_server_name(self, server_name)


def _alpn_list_to_str(alpn_list):
    """
    Transform ['h2', 'http/1.1'] -> "h2;http/1.1"
    None is returned if list is None or empty
    """
    if alpn_list:
        assert not isinstance(alpn_list, str)
        return ';'.join(alpn_list)
    return None


def is_alpn_available():
    """Returns True if Application Layer Protocol Negotiation (ALPN)
    is supported on this system."""
    return _awscrt.is_alpn_available()


class InputStream(NativeResource):
    """InputStream allows `awscrt` native code to read from Python binary I/O classes.

    Args:
        stream (io.IOBase): Python binary I/O stream to wrap.
    """
    __slots__ = ('_stream')
    # TODO: Implement IOBase interface so Python can read from this class as well.

    def __init__(self, stream):
        # duck-type instead of checking inheritance from IOBase.
        # At the least, stream must have read()
        if not callable(getattr(stream, 'read', None)):
            raise TypeError('I/O stream type expected')
        assert not isinstance(stream, InputStream)

        super().__init__()
        self._stream = stream
        self._binding = _awscrt.input_stream_new(self)

    def _read_into_memoryview(self, m):
        # Read into memoryview m.
        # Return number of bytes read, or None if no data available.
        try:
            # prefer the most efficient read methods,
            if hasattr(self._stream, 'readinto1'):
                return self._stream.readinto1(m)
            if hasattr(self._stream, 'readinto'):
                return self._stream.readinto(m)

            if hasattr(self._stream, 'read1'):
                data = self._stream.read1(len(m))
            else:
                data = self._stream.read(len(m))
            n = len(data)
            m[:n] = data
            return n
        except BlockingIOError:
            return None

    def _seek(self, offset, whence):
        return self._stream.seek(offset, whence)

    @classmethod
    def wrap(cls, stream, allow_none=False):
        """
        Given some stream type, returns an :class:`InputStream`.

        Args:
            stream (Union[io.IOBase, InputStream, None]): Binary I/O stream to wrap.
            allow_none (bool): Whether to allow `stream` to be None.
                If False (default), and `stream` is None, an exception is raised.

        Returns:
            Union[InputStream, None]: If `stream` is already an :class:`InputStream`, it is returned.
            Otherwise, an :class:`InputStream` which wraps the `stream` is returned.
            If `allow_none` is True, and `stream` is None, then None is returned.
        """
        if stream is None and allow_none:
            return None
        if isinstance(stream, InputStream):
            return stream
        return cls(stream)


class Pkcs11Lib(NativeResource):
    """
    Handle to a loaded PKCS#11 library.

    For most use cases, a single instance of :class:`Pkcs11Lib` should be used for the
    lifetime of your application.

    Keyword Args:
        file (str): Path to PKCS#11 library.
        behavior (Optional[InitializeFinalizeBehavior]):
            Specifies how `C_Initialize()` and `C_Finalize()` will be called
            on the PKCS#11 library (default is :attr:`InitializeFinalizeBehavior.DEFAULT`)
    """

    class InitializeFinalizeBehavior(IntEnum):
        """
        An enumeration.

        Controls how `C_Initialize()` and `C_Finalize()` are called on the PKCS#11 library.
        """

        DEFAULT = 0
        """
        Relaxed behavior that accommodates most use cases.

        `C_Initialize()` is called on creation, and "already-initialized"
        errors are ignored. `C_Finalize()` is never called, just in case
        another part of your application is still using the PKCS#11 library.
        """

        OMIT = 1
        """
        Skip calling `C_Initialize()` and `C_Finalize()`.

        Use this if your application has already initialized the PKCS#11 library, and
        you do not want `C_Initialize()` called again.
        """

        STRICT = 2
        """
        `C_Initialize()` is called on creation and `C_Finalize()` is
        called on cleanup.

        If `C_Initialize()` reports that's it's already initialized, this is
        treated as an error. Use this if you need perfect cleanup (ex: running
        valgrind with --leak-check).
        """

    def __init__(self, *, file: str, behavior: InitializeFinalizeBehavior = None):
        super().__init__()
        if behavior is None:
            behavior = Pkcs11Lib.InitializeFinalizeBehavior.DEFAULT

        self._binding = _awscrt.pkcs11_lib_new(file, behavior)
