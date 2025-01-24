"""
event-stream RPC (remote procedure call) protocol library for `awscrt`.
"""

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.

import _awscrt
from abc import ABC, abstractmethod
from awscrt import NativeResource
import awscrt.exceptions
from awscrt.eventstream import Header
from awscrt.io import ClientBootstrap, SocketOptions, TlsConnectionOptions
from collections.abc import Callable
from concurrent.futures import Future
from enum import IntEnum
from functools import partial
from typing import Optional, Sequence, Union

__all__ = [
    'MessageType',
    'MessageFlag',
    'ClientConnectionHandler',
    'ClientConnection',
    'ClientContinuation',
    'ClientContinuationHandler',
]


class MessageType(IntEnum):
    """Types of messages in the event-stream RPC protocol.

    The :attr:`~MessageType.APPLICATION_MESSAGE` and :attr:`~MessageType.APPLICATION_ERROR` types may only be sent
    on streams, and will never arrive as a protocol message (stream-id 0).

    For all other message types, they may only be sent as protocol messages
    (stream-id 0), and will never arrive as a stream message.

    Different message types expect specific headers and flags, consult documentation."""

    APPLICATION_MESSAGE = 0
    """Application message"""

    APPLICATION_ERROR = 1
    """Application error"""

    PING = 2
    """Ping"""

    PING_RESPONSE = 3
    """Ping response"""

    CONNECT = 4
    """Connect"""

    CONNECT_ACK = 5
    """Connect acknowledgement

    If the :attr:`MessageFlag.CONNECTION_ACCEPTED` flag is not present, the connection has been rejected."""

    PROTOCOL_ERROR = 6
    """Protocol error"""

    INTERNAL_ERROR = 7
    """Internal error"""

    def __format__(self, format_spec):
        # override so formatted string doesn't simply look like an int
        return str(self)


class MessageFlag:
    """Flags for messages in the event-stream RPC protocol.

    Flags may be XORed together.
    Not all flags can be used with all message types, consult documentation.
    """
    # TODO: when python 3.5 is dropped this class should inherit from IntFlag.
    # When doing this, be sure to update type-hints and callbacks to pass
    # MessageFlag instead of plain int.

    NONE = 0
    """No flags"""

    CONNECTION_ACCEPTED = 0x1
    """Connection accepted

    If this flag is absent from a :attr:`MessageType.CONNECT_ACK`, the connection has been rejected."""

    TERMINATE_STREAM = 0x2
    """Terminate stream

    This message may be used with any message type.
    The sender will close their connection after the message is written to the wire.
    The receiver will close their connection after delivering the message to the user."""

    def __format__(self, format_spec):
        # override so formatted string doesn't simply look like an int
        return str(self)


class ClientConnectionHandler(ABC):
    """Base class for handling connection events.

    Inherit from this class and override methods to handle connection events.
    All callbacks for this connection will be invoked on the same thread,
    and :meth:`on_connection_setup()` will always be the first callback invoked.
    """

    @abstractmethod
    def on_connection_setup(self, connection, error, **kwargs) -> None:
        """Invoked upon completion of the setup attempt.

        If setup was successful, the connection is provided to the user.

        Note that the network connection stays alive until it is closed,
        even if no local references to the connection object remain.
        The user should store a reference to this connection, and call
        `connection.close()` when they are done with it to avoid leaking
        resources.

        Setup will always be the first callback invoked on the handler.
        If setup failed, no further callbacks will be invoked on this handler.

        Args:
            connection: The connection, if setup was successful,
                or None if setup failed.

            error: None, if setup was successful, or an Exception
                if setup failed.

            `**kwargs`: Forward compatibility kwargs.
        """
        pass

    @abstractmethod
    def on_connection_shutdown(self, reason: Optional[Exception], **kwargs) -> None:
        """Invoked when the connection finishes shutting down.

        This event will not be invoked if connection setup failed.

        Args:
            reason: Reason will be None if the user initiated the shutdown,
                otherwise the reason will be an Exception.

            **kwargs: Forward compatibility kwargs.
        """
        pass

    @abstractmethod
    def on_protocol_message(
            self,
            headers: Sequence[Header],
            payload: bytes,
            message_type: MessageType,
            flags: int,
            **kwargs) -> None:
        """Invoked when a message for the connection (stream-id 0) is received.

        Args:
            headers: Message headers.

            payload: Binary message payload.

            message_type: Message type.

            flags: Message flags. Values from :class:`MessageFlag` may be
                XORed together. Not all flags can be used with all message
                types, consult documentation.

            **kwargs: Forward compatibility kwargs.
        """

        pass


def _to_binding_msg_args(headers, payload, message_type, flags):
    """
    Transform args that a python send-msg function would take,
    into args that a native send-msg function would take.
    """
    # python functions for sending messages
    if headers is None:
        headers = []
    else:
        headers = [i._as_binding_tuple() for i in headers]
    if payload is None:
        payload = b''
    if flags is None:
        flags = MessageFlag.NONE
    return (headers, payload, message_type, flags)


def _from_binding_msg_args(headers, payload, message_type, flags):
    """
    Transform msg-received args that came from native,
    into msg-received args presented to python users.
    """
    headers = [Header._from_binding_tuple(i) for i in headers]
    if payload is None:
        payload = b''
    message_type = MessageType(message_type)
    return (headers, payload, message_type, flags)


def _on_message_flush(bound_future, bound_callback, error_code):
    # invoked when a message is flushed (written to wire), or canceled due to connection error.
    e = awscrt.exceptions.from_code(error_code) if error_code else None
    try:
        if bound_callback:
            bound_callback(error=e)
    finally:
        # ensure future completes, even if user callback had unhandled exception
        if error_code:
            bound_future.set_exception(e)
        else:
            bound_future.set_result(None)


class ClientConnection(NativeResource):
    """A client connection for the event-stream RPC protocol.

    Use :meth:`ClientConnection.connect()` to establish a new
    connection.

    Note that the network connection stays alive until it is closed,
    even if no local references to the connection object remain.
    The user should store a reference to any connections, and call
    :meth:`close()` when they are done with them to avoid leaking resources.

    Attributes:
        host_name (str): Remote host name.

        port (int): Remote port.

        shutdown_future (concurrent.futures.Future[None]): Completes when this
            connection has finished shutting down. Future will contain a
            result of None, or an exception indicating why shutdown occurred.
    """

    __slots__ = ['host_name', 'port', 'shutdown_future', '_connect_future', '_handler']

    def __init__(self, host_name, port, handler):
        # Do no instantiate directly, use static connect method
        super().__init__()
        self.host_name = host_name  # type: str
        self.port = port  # type: int
        self.shutdown_future = Future()  # type: Future
        self.shutdown_future.set_running_or_notify_cancel()  # prevent cancel
        self._connect_future = Future()  # type: Future
        self._connect_future.set_running_or_notify_cancel()  # prevent cancel
        self._handler = handler  # type: ClientConnectionHandler

    @classmethod
    def connect(
            cls,
            *,
            handler: ClientConnectionHandler,
            host_name: str,
            port: int,
            bootstrap: ClientBootstrap = None,
            socket_options: Optional[SocketOptions] = None,
            tls_connection_options: Optional[TlsConnectionOptions] = None) -> 'concurrent.futures.Future':
        """Asynchronously establish a new ClientConnection.

        Args:
            handler: Handler for connection events.

            host_name: Connect to host.

            port: Connect to port.

            bootstrap: Client bootstrap to use when initiating socket connection.
                If None is provided, the default singleton is used.

            socket_options: Optional socket options.
                If None is provided, then default options are used.

            tls_connection_options: Optional TLS
                connection options. If None is provided, then the connection will
                be attempted over plain-text.

        Returns:
            concurrent.futures.Future: A Future which completes when the connection succeeds or fails.
            If successful, the Future will contain None.
            Otherwise it will contain an exception.
            If the connection is successful, it will be made available via
            the handler's on_connection_setup callback.
            Note that this network connection stays alive until it is closed,
            even if no local references to the connection object remain.
            The user should store a reference to any connections, and call
            :meth:`close()` when they are done with them to avoid leaking resources.
        """

        if not socket_options:
            socket_options = SocketOptions()

        # Connection is not made available to user until setup callback fires
        connection = cls(host_name, port, handler)

        if not bootstrap:
            bootstrap = ClientBootstrap.get_or_create_static_default()

        # connection._binding is set within the following call */
        _awscrt.event_stream_rpc_client_connection_connect(
            host_name,
            port,
            bootstrap,
            socket_options,
            tls_connection_options,
            connection)

        return connection._connect_future

    def _on_connection_setup(self, error_code):
        if error_code:
            connection = None
            error = awscrt.exceptions.from_code(error_code)
        else:
            connection = self
            error = None

        try:
            self._handler.on_connection_setup(connection=connection, error=error)
        finally:
            # ensure future completes, even if user callback had unhandled exception
            if error:
                self._connect_future.set_exception(error)
            else:
                self._connect_future.set_result(None)

    def _on_connection_shutdown(self, error_code):
        reason = awscrt.exceptions.from_code(error_code) if error_code else None
        try:
            self._handler.on_connection_shutdown(reason=reason)
        finally:
            # ensure future completes, even if user callback had unhandled exception
            if reason:
                self.shutdown_future.set_exception(reason)
            else:
                self.shutdown_future.set_result(None)

    def _on_protocol_message(self, headers, payload, message_type, flags):
        # transform from simple types to actual classes
        headers, payload, message_type, flags = _from_binding_msg_args(headers, payload, message_type, flags)
        self._handler.on_protocol_message(
            headers=headers,
            payload=payload,
            message_type=message_type,
            flags=flags)

    def close(self):
        """Close the connection.

        Shutdown is asynchronous. This call has no effect if the connection is
        already closed or closing.

        Note that, if the network connection hasn't already ended,
        `close()` MUST be called to avoid leaking resources. The network
        connection will not terminate simply because there are no references
        to the connection object.

        Returns:
            concurrent.futures.Future: This connection's :attr:`shutdown_future`,
            which completes when shutdown has finished.
        """
        # TODO: let user pass their own exception/error-code/reason for closing
        _awscrt.event_stream_rpc_client_connection_close(self._binding)
        return self.shutdown_future

    def is_open(self):
        """
        Returns:
            bool: True if this connection is open and usable, False otherwise.
            Check :attr:`shutdown_future` to know when the connection is completely
            finished shutting down.
        """
        return _awscrt.event_stream_rpc_client_connection_is_open(self._binding)

    def send_protocol_message(
            self,
            *,
            headers: Optional[Sequence[Header]] = None,
            payload: Optional[Union[bytes, bytearray]] = None,
            message_type: MessageType,
            flags: Optional[int] = None,
            on_flush: Callable = None) -> 'concurrent.futures.Future':
        """Send a protocol message.

        Protocol messages use stream-id 0.

        Use the returned future, or the `on_flush` callback, to be informed
        when the message is successfully written to the wire, or fails to send.

        Keyword Args:
            headers: Message headers.

            payload: Binary message payload.

            message_type: Message type.

            flags: Message flags. Values from :class:`MessageFlag` may be
                XORed together. Not all flags can be used with all message
                types, consult documentation.

            on_flush: Callback invoked when the message is successfully written
                to the wire, or fails to send. The function should take the
                following arguments and return nothing:

                    *   `error` (Optional[Exception]): None if the message was
                        successfully written to the wire, or an Exception
                        if it failed to send.

                    *   `**kwargs` (dict): Forward compatibility kwargs.

                This callback is always invoked on the connection's event-loop
                thread.

        Returns:
            A future which completes with a result of None if the
            message is successfully written to the wire,
            or an exception if the message fails to send.
        """
        future = Future()
        future.set_running_or_notify_cancel()  # prevent cancel

        # native code deals with simplified types
        headers, payload, message_type, flags = _to_binding_msg_args(headers, payload, message_type, flags)

        _awscrt.event_stream_rpc_client_connection_send_protocol_message(
            self._binding,
            headers,
            payload,
            message_type,
            flags,
            partial(_on_message_flush, future, on_flush))
        return future

    def new_stream(self, handler: 'ClientContinuationHandler') -> 'ClientContinuation':
        """
        Create a new stream.

        The stream will send no data until :meth:`ClientContinuation.activate()`
        is called. Call activate() when you're ready for callbacks and events to fire.

        Args:
            handler: Handler to process continuation messages and state changes.

        Returns:
            The new continuation object.
        """
        continuation = ClientContinuation(handler, self)
        continuation._binding = _awscrt.event_stream_rpc_client_connection_new_stream(self)
        return continuation


class ClientContinuation(NativeResource):
    """
    A continuation of messages on a given stream-id.

    Create with :meth:`ClientConnection.new_stream()`.

    The stream will send no data until :meth:`ClientContinuation.activate()`
    is called. Call activate() when you're ready for callbacks and events to fire.

    Attributes:
        connection (ClientConnection): This stream's connection.

        closed_future (concurrent.futures.Future) : Future which completes with a result of None
            when the continuation has closed.
    """

    def __init__(self, handler, connection):
        # Do not instantiate directly, use ClientConnection.new_stream()
        super().__init__()
        self._handler = handler
        self.connection = connection  # type: ClientConnection
        self.closed_future = Future()  # type: Future
        self.closed_future.set_running_or_notify_cancel()  # prevent cancel

    def activate(
            self,
            *,
            operation: str,
            headers: Sequence[Header] = None,
            payload: Union[bytes, bytearray] = None,
            message_type: MessageType,
            flags: int = None,
            on_flush: Callable = None):
        """
        Activate the stream by sending its first message.

        Use the returned future, or the `on_flush` callback, to be informed
        when the message is successfully written to the wire, or fails to send.

        activate() may only be called once, use send_message() to write further
        messages on this stream-id.

        Keyword Args:
            operation: Operation name for this stream.

            headers: Message headers.

            payload: Binary message payload.

            message_type: Message type.

            flags: Message flags. Values from :class:`MessageFlag` may be
                XORed together. Not all flags can be used with all message
                types, consult documentation.

            on_flush: Callback invoked when the message is successfully written
                to the wire, or fails to send. The function should take the
                following arguments and return nothing:

                    *   `error` (Optional[Exception]): None if the message was
                        successfully written to the wire, or an Exception
                        if it failed to send.

                    *   `**kwargs` (dict): Forward compatibility kwargs.

                This callback is always invoked on the connection's event-loop
                thread.

        Returns:
            A future which completes with a result of None if the
            message is successfully written to the wire,
            or an exception if the message fails to send.
        """

        flush_future = Future()
        flush_future.set_running_or_notify_cancel()  # prevent cancel

        # native code deals with simplified types
        headers, payload, message_type, flags = _to_binding_msg_args(headers, payload, message_type, flags)

        _awscrt.event_stream_rpc_client_continuation_activate(
            self._binding,
            # don't give binding a reference to self until activate() is called.
            # this reference is used for invoking callbacks, and its existence
            # keeps the python object alive until the closed callback fires
            self,
            operation,
            headers,
            payload,
            message_type,
            flags,
            partial(_on_message_flush, flush_future, on_flush))

        return flush_future

    def send_message(
            self,
            *,
            headers: Sequence[Header] = None,
            payload: Union[bytes, bytearray] = None,
            message_type: MessageType,
            flags: int = None,
            on_flush: Callable = None) -> 'concurrent.futures.Future':
        """
        Send a continuation message.

        Use the returned future, or the `on_flush` callback, to be informed
        when the message is successfully written to the wire, or fails to send.

        Note that the the first message on a stream-id must be sent with activate(),
        send_message() is for all messages that follow.

        Keyword Args:
            operation: Operation name for this stream.

            headers: Message headers.

            payload: Binary message payload.

            message_type: Message type.

            flags: Message flags. Values from :class:`MessageFlag` may be
                XORed together. Not all flags can be used with all message
                types, consult documentation.

            on_flush: Callback invoked when the message is successfully written
                to the wire, or fails to send. The function should take the
                following arguments and return nothing:

                    *   `error` (Optional[Exception]): None if the message was
                        successfully written to the wire, or an Exception
                        if it failed to send.

                    *   `**kwargs` (dict): Forward compatibility kwargs.

                This callback is always invoked on the connection's event-loop
                thread.

        Returns:
            A future which completes with a result of None if the
            message is successfully written to the wire,
            or an exception if the message fails to send.
        """
        future = Future()
        future.set_running_or_notify_cancel()  # prevent cancel
        # native code deals with simplified types
        headers, payload, message_type, flags = _to_binding_msg_args(headers, payload, message_type, flags)

        _awscrt.event_stream_rpc_client_continuation_send_message(
            self._binding,
            headers,
            payload,
            message_type,
            flags,
            partial(_on_message_flush, future, on_flush))
        return future

    def is_closed(self):
        return _awscrt.event_stream_rpc_client_continuation_is_closed(self._binding)

    def _on_continuation_closed(self):
        try:
            self._handler.on_continuation_closed()
        finally:
            # ensure future completes, even if user callback had unhandled exception
            self.closed_future.set_result(None)

    def _on_continuation_message(self, headers, payload, message_type, flags):
        # transform from simple types to actual classes
        headers, payload, message_type, flags = _from_binding_msg_args(headers, payload, message_type, flags)
        self._handler.on_continuation_message(
            headers=headers,
            payload=payload,
            message_type=message_type,
            flags=flags)


class ClientContinuationHandler(ABC):
    """Base class for handling stream continuation events.

    Inherit from this class and override methods to handle events.
    All callbacks will be invoked on the same thread (the same thread used by
    the connection).

    A common pattern is to store the continuation within its handler.
    Example::

        continuation_handler.continuation = connection.new_stream(continuation_handler)
    """

    @abstractmethod
    def on_continuation_message(
            self,
            headers: Sequence[Header],
            payload: bytes,
            message_type: MessageType,
            flags: int,
            **kwargs) -> None:
        """Invoked when a message is received on this continuation.

        Args:
            headers: Message headers.

            payload: Binary message payload.

            message_type: Message type.

            flags: Message flags. Values from :class:`MessageFlag` may be
                XORed together. Not all flags can be used with all message
                types, consult documentation.

            **kwargs: Forward compatibility kwargs.
        """
        pass

    @abstractmethod
    def on_continuation_closed(self, **kwargs) -> None:
        """Invoked when the continuation is closed.

        Once the continuation is closed, no more messages may be sent or received.
        The continuation is closed when a message is sent or received with
        the TERMINATE_STREAM flag, or when the connection shuts down.

        Args:
            **kwargs: Forward compatibility kwargs.
        """
        pass
