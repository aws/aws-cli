"""
WebSocket - `RFC 6455 <https://www.rfc-editor.org/rfc/rfc6455>`_

Use the :func:`connect()` to establish a :class:`WebSocket` client connection.

Note from the developer: This is a very low-level API, which forces the
user to deal with things like data fragmentation.
A higher-level API could easily be built on top of this.

.. _authoring-callbacks:

Authoring Callbacks
-------------------
All network operations in `awscrt.websocket` are asynchronous.
Callbacks are always invoked on the WebSocket's networking thread.
You MUST NOT perform blocking network operations from any callback, or you will cause a deadlock.
For example: do not send a frame, and then wait for that frame to complete,
within a callback. The WebSocket cannot do work until your callback returns,
so the thread will be stuck. You can send the frame from within the callback,
just don't wait for it to complete within the callback.

If you want to do blocking waits, do it from a thread you control, like the main thread.
It's fine for the main thread to send a frame, and wait until it completes.

All functions and methods in `awscrt.websocket` are thread-safe.
They can be called from any mix of threads.

.. _flow-control-reading:

Flow Control (reading)
----------------------
By default, the WebSocket will read from the network as fast as it can hand you the data.
You must prevent the WebSocket from reading data faster than you can process it,
or memory usage could balloon until your application explodes.

There are two ways to manage this.

First, and simplest, is to process incoming data synchronously within the
`on_incoming_frame` callbacks. Since callbacks are invoked on the WebSocket's
networking thread, the WebSocket cannot read more data until the callback returns.
Therefore, processing the data in a synchronous manner
(i.e. writing to disk, printing to screen, etc) will naturally
affect `TCP flow control <https://en.wikipedia.org/wiki/Transmission_Control_Protocol#Flow_control>`_,
and prevent data from arriving too fast. However, you MUST NOT perform a blocking
network operation from within the callback or you risk deadlock (see :ref:`authoring-callbacks`).

The second, more complex, way requires you to manage the size of the read window.
Do this if you are processing the data asynchronously
(i.e. sending the data along on another network connection).
Create the WebSocket with `manage_read_window` set true,
and set `initial_read_window` to the number of bytes you are ready to receive right away.
Whenever the read window reaches 0, you will stop receiving anything.
The read window shrinks as you receive the payload from "data" frames (TEXT, BINARY, CONTINUATION).
Call :meth:`WebSocket.increment_read_window()` to increase the window again keep frames flowing in.
You only need to worry about the payload from "data" frames.
The WebSocket automatically increments its window to account for any
other incoming bytes, including other parts of a frame (opcode, payload-length, etc)
and the payload of other frame types (PING, PONG, CLOSE).
You'll probably want to do it like this:
Pick the max amount of memory to buffer, and set this as the `initial_read_window`.
When data arrives, the window has shrunk by that amount.
Send this data along on the other network connection.
When that data is done sending, call `increment_read_window()`
by the amount you just finished sending.
If you don't want to receive any data at first, set the `initial_read_window` to 0,
and `increment_read_window()` when you're ready.
Maintaining a larger window is better for overall throughput.

.. _flow-control-writing:

Flow Control (writing)
----------------------
You must also ensure that you do not continually send frames faster than the other
side can read them, or memory usage could balloon until your application explodes.

The simplest approach is to only send 1 frame at a time.
Use the :meth:`WebSocket.send_frame()` `on_complete` callback to know when the send is complete.
Then you can try and send another.

A more complex, but higher throughput, way is to let multiple frames be in flight
but have a cap. If the number of frames in flight, or bytes in flight, reaches
your cap then wait until some frames complete before trying to send more.

.. _api:

API
---
"""

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.
import _awscrt
from awscrt import NativeResource
import awscrt.exceptions
from awscrt.http import HttpProxyOptions, HttpRequest
from awscrt.io import ClientBootstrap, TlsConnectionOptions, SocketOptions
from dataclasses import dataclass
from enum import IntEnum
import sys
from typing import Callable, Optional, Sequence, Tuple, Union


class Opcode(IntEnum):
    """An opcode defines a frame's type.

    RFC 6455 classifies TEXT and BINARY as `data frames <https://www.rfc-editor.org/rfc/rfc6455#section-5.6>`_.
    A CONTINUATION frame "continues" the most recent data frame.
    All other opcodes are for `control frames <https://www.rfc-editor.org/rfc/rfc6455#section-5.5>`_.
    """

    CONTINUATION = 0x0,
    """Continues the most recent TEXT or BINARY data frame.

    See `RFC 6455 section 5.4 - Fragmentation <https://www.rfc-editor.org/rfc/rfc6455#section-5.4>`_.
    """

    TEXT = 0x1
    """The data frame for sending text.

    The payload must contain UTF-8."""

    BINARY = 0x2
    """The data frame for sending binary."""

    CLOSE = 0x8
    """The control frame which is the final frame sent by an endpoint.

    The CLOSE frame may include a payload, but its format is very particular.
    See `RFC 6455 section 5.5.1 <https://www.rfc-editor.org/rfc/rfc6455#section-5.5.1>`_.
    """

    PING = 0x9
    """A control frame that may serve as either a keepalive or as a means to verify
    that the remote endpoint is still responsive.

    DO NOT manually send a PONG frame in response to a PING,
    the implementation does this automatically.

    A PING frame may include a payload.
    See `RFC 6455 section 5.5.2 <https://www.rfc-editor.org/rfc/rfc6455#section-5.5.2>`_.
    """

    PONG = 0xA
    """The control frame that is the response to a PING frame.

    DO NOT manually send a PONG frame in response to a PING,
    the implementation does this automatically.

    See `RFC 6455 section 5.5.3 <https://www.rfc-editor.org/rfc/rfc6455#section-5.5.3>`_.
    """

    def is_data_frame(self):
        """True if this is a "data frame" opcode.

        TEXT, BINARY, and CONTINUATION are "data frames". The rest are "control" frames.

        If the WebSocket was created with `manage_read_window`,
        then the read window shrinks as "data frames" are received.
        See :ref:`flow-control-reading` for a thorough explanation.
        """
        return self.value in (Opcode.TEXT, Opcode.BINARY, Opcode.CONTINUATION)


MAX_PAYLOAD_LENGTH = 0x7FFFFFFFFFFFFFFF
"""The maximum frame payload length allowed by RFC 6455"""


@dataclass
class OnConnectionSetupData:
    """Data passed to the `on_connection_setup` callback"""

    exception: Optional[Exception] = None
    """If the connection failed, this exception explains why.

    This is None if the connection succeeded."""

    websocket: Optional['WebSocket'] = None
    """If the connection succeeded, here's the WebSocket.

    You should store this WebSocket somewhere
    (the connection will shut down if the class is garbage collected).

    This is None if the connection failed.
    """

    handshake_response_status: Optional[int] = None
    """The HTTP response status-code, if you're interested.

    This is present if an HTTP response was received, regardless of whether
    the handshake was accepted or rejected. This always has the value 101
    for successful connections.

    This is None if the connection failed before receiving an HTTP response.
    """

    handshake_response_headers: Optional[Sequence[Tuple[str, str]]] = None
    """The HTTP response headers, if you're interested.

    These are present if an HTTP response was received, regardless of whether
    the handshake was accepted or rejected.

    This is None if the connection failed before receiving an HTTP response.
    """

    handshake_response_body: bytes = None
    """The HTTP response body, if you're interested.

    This is only present if the server sent a full HTTP response rejecting the handshake.
    It is not present if the connection succeeded,
    or the connection failed for other reasons.
    """


@dataclass
class OnConnectionShutdownData:
    """Data passed to the `on_connection_shutdown` callback"""

    exception: Optional[Exception] = None
    """If the connection shut down cleanly, this is None.

    If the connection shut down due to error, or an error occurs while
    shutting down, this exception explains why."""


@dataclass
class IncomingFrame:
    """Describes the frame you are receiving.

    Used in `on_incoming_frame` callbacks """

    opcode: Opcode
    """This frame's opcode."""

    payload_length: int
    """This frame's payload length (in bytes)."""

    fin: bool
    """The FIN bit indicates whether this is the final fragment in a message.

    See `RFC 6455 section 5.4 - Fragmentation <https://www.rfc-editor.org/rfc/rfc6455#section-5.4>`_"""

    def is_data_frame(self):
        """True if this is a "data frame".

        TEXT, BINARY, and CONTINUATION are "data frames". The rest are "control frames".

        If the WebSocket was created with `manage_read_window`,
        then the read window shrinks as "data frames" are received.
        See :ref:`flow-control-reading` for a thorough explanation.
        """
        return self.opcode.is_data_frame()


@dataclass
class OnIncomingFrameBeginData:
    """Data passed to the `on_incoming_frame_begin` callback.

    Each `on_incoming_frame_begin` call will be followed by
    0+ `on_incoming_frame_payload` calls,
    followed by one `on_incoming_frame_complete` call."""

    frame: IncomingFrame
    """Describes the frame you are starting to receive."""


@dataclass
class OnIncomingFramePayloadData:
    """Data passed to the `on_incoming_frame_payload` callback.

    This callback will be invoked 0+ times.
    Each time, `data` will contain a bit more of the payload.
    Once all `frame.payload_length` bytes have been received
    (or the network connection is lost), the `on_incoming_frame_complete`
    callback will be invoked.

    If the WebSocket was created with `manage_read_window`,
    and this is a "data frame" (TEXT, BINARY, CONTINUATION),
    then the read window shrinks by `len(data)`.
    See :ref:`flow-control-reading` for a thorough explanation.
    """

    frame: IncomingFrame
    """Describes the frame whose payload you are receiving."""

    data: bytes
    """The next chunk of this frame's payload."""


@dataclass
class OnIncomingFrameCompleteData:
    """Data passed to the `on_incoming_frame_complete` callback."""

    frame: IncomingFrame
    """Describes the frame you are done receiving."""

    exception: Optional[Exception] = None
    """If `exception` is set, then something went wrong processing the frame
    or the connection was lost before the frame was fully received."""


@dataclass
class OnSendFrameCompleteData:
    """Data passed to the :meth:`WebSocket.send_frame()` `on_complete` callback."""

    exception: Optional[Exception] = None
    """If `exception` is set, the connection was lost before this frame could be completely sent.

    If `exception` is None, the frame was successfully written to the OS socket.
    Note that this data may still be buffered in the OS, it has
    not necessarily left this machine or reached the other endpoint yet."""


class WebSocket(NativeResource):
    """A WebSocket connection.

    Use :meth:`connect()` to establish a new client connection.
    """

    def __init__(self, binding):
        # Do not init a WebSocket directly, use websocket.connect()
        super().__init__()
        self._binding = binding

    def close(self):
        """Close the WebSocket asynchronously.

        You should call this when you are done with a healthy WebSocket,
        to ensure that it shuts down and cleans up.
        You don't need to call this on a WebSocket that has already shut
        down, or is in the middle of shutting down, but it is safe to do so.
        This function is idempotent.

        To determine when shutdown has completed, you can use the
        `on_shutdown_complete` callback (passed into :meth:`connect()`).
        """
        _awscrt.websocket_close(self._binding)

    def send_frame(
        self,
        opcode: Opcode,
        payload: Optional[Union[str, bytes, bytearray, memoryview]] = None,
        *,
        fin: bool = True,
        on_complete: Optional[Callable[[OnSendFrameCompleteData], None]] = None,
    ):
        """Send a WebSocket frame asynchronously.

        See `RFC 6455 section 5 - Data Framing <https://www.rfc-editor.org/rfc/rfc6455#section-5>`_
        for details on all frame types.

        This is a low-level API, which requires you to send the appropriate payload for each type of opcode.
        If you are not an expert, stick to sending :attr:`Opcode.TEXT` or :attr:`Opcode.BINARY` frames,
        and don't touch the FIN bit.

        See :ref:`flow-control-writing` to learn about limiting the amount of
        unsent data buffered in memory.

        Args:
            opcode: :class:`Opcode` for this frame.

            payload: Any `bytes-like object <https://docs.python.org/3/glossary.html#term-bytes-like-object>`_.
                `str` will always be encoded as UTF-8. It is fine to pass a `str` for a BINARY frame.
                None will result in an empty payload, the same as passing empty `bytes()`

            fin: The FIN bit indicates that this is the final fragment in a message.
                Do not set this False unless you understand
                `WebSocket fragmentation <https://www.rfc-editor.org/rfc/rfc6455#section-5.4>`_

            on_complete: Optional callback, invoked when the frame has finished sending.
                Takes a single :class:`OnSendFrameCompleteData` argument.

                If :attr:`OnSendFrameCompleteData.exception` is set, the connection
                was lost before this frame could be completely sent.

                But if `exception` is None, the frame was successfully written to the OS socket.
                (This doesn't mean the other endpoint has received the data yet,
                or even guarantee that the data has left the machine yet,
                but it's on track to get there).

                Be sure to read about :ref:`authoring-callbacks`.
        """
        def _on_complete(error_code):
            cbdata = OnSendFrameCompleteData()
            if error_code:
                cbdata.exception = awscrt.exceptions.from_code(error_code)

            # Do not let exceptions from the user's callback bubble up any further.
            try:
                if on_complete is not None:
                    on_complete(cbdata)
            except BaseException:
                print("Exception in WebSocket.send_frame on_complete callback", file=sys.stderr)
                sys.excepthook(*sys.exc_info())
                self.close()

        _awscrt.websocket_send_frame(
            self._binding,
            Opcode(opcode),  # needless cast to ensure opcode is valid
            payload,
            fin,
            _on_complete)

    def increment_read_window(self, size: int):
        """Manually increment the read window by this many bytes, to continue receiving frames.

        See :ref:`flow-control-reading` for a thorough explanation.
        If the WebSocket was created without `manage_read_window`, this function does nothing.
        This function may be called from any thread.

        Args:
            size: in bytes
        """
        if size < 0:
            raise ValueError("Increment size cannot be negative")

        _awscrt.websocket_increment_read_window(self._binding, size)


class _WebSocketCore(NativeResource):
    # Private class that handles wrangling callback data from C -> Python.
    # This class is kept alive by C until the final callback occurs.
    #
    # The only reason this class inherits from NativeResource,
    # is so our tests will tell us if the memory leaks.

    def __init__(self,
                 on_connection_setup,
                 on_connection_shutdown,
                 on_incoming_frame_begin,
                 on_incoming_frame_payload,
                 on_incoming_frame_complete):
        super().__init__()
        self._on_connection_setup_cb = on_connection_setup
        self._on_connection_shutdown_cb = on_connection_shutdown
        self._on_incoming_frame_begin_cb = on_incoming_frame_begin
        self._on_incoming_frame_payload_cb = on_incoming_frame_payload
        self._on_incoming_frame_complete_cb = on_incoming_frame_complete

    def _on_connection_setup(
            self,
            error_code,
            websocket_binding,
            handshake_response_status,
            handshake_response_headers,
            handshake_response_body):

        cbdata = OnConnectionSetupData()
        if error_code:
            cbdata.exception = awscrt.exceptions.from_code(error_code)
        else:
            cbdata.websocket = WebSocket(websocket_binding)

        cbdata.handshake_response_status = handshake_response_status
        cbdata.handshake_response_headers = handshake_response_headers
        cbdata.handshake_response_body = handshake_response_body

        # Do not let exceptions from the user's callback bubble up any further.
        try:
            self._on_connection_setup_cb(cbdata)
        except BaseException:
            print("Exception in WebSocket on_connection_setup callback", file=sys.stderr)
            sys.excepthook(*sys.exc_info())
            if cbdata.websocket is not None:
                cbdata.websocket.close()

    def _on_connection_shutdown(self, error_code):
        cbdata = OnConnectionShutdownData()
        if error_code:
            cbdata.exception = awscrt.exceptions.from_code(error_code)

        # Do not let exceptions from the user's callback bubble up any further.
        try:
            if self._on_connection_shutdown_cb is not None:
                self._on_connection_shutdown_cb(cbdata)
        except BaseException:
            print("Exception in WebSocket on_connection_shutdown callback", file=sys.stderr)
            sys.excepthook(*sys.exc_info())

    def _on_incoming_frame_begin(self, opcode_int, payload_length, fin):
        self._current_incoming_frame = IncomingFrame(Opcode(opcode_int), payload_length, fin)

        cbdata = OnIncomingFrameBeginData(self._current_incoming_frame)

        # Do not let exceptions from the user's callback bubble up any further:
        try:
            if self._on_incoming_frame_begin_cb is not None:
                self._on_incoming_frame_begin_cb(cbdata)
        except BaseException:
            print("Exception in WebSocket on_incoming_frame_begin callback", file=sys.stderr)
            sys.excepthook(*sys.exc_info())
            return False  # close websocket

        return True

    def _on_incoming_frame_payload(self, data):
        cbdata = OnIncomingFramePayloadData(self._current_incoming_frame, data)

        # Do not let exceptions from the user's callback bubble up any further:
        try:
            if self._on_incoming_frame_payload_cb is not None:
                self._on_incoming_frame_payload_cb(cbdata)
        except BaseException:
            print("Exception in WebSocket on_incoming_frame_payload callback", file=sys.stderr)
            sys.excepthook(*sys.exc_info())
            return False  # close websocket

        return True

    def _on_incoming_frame_complete(self, error_code):
        cbdata = OnIncomingFrameCompleteData(self._current_incoming_frame)
        if error_code:
            cbdata.exception = awscrt.exceptions.from_code(error_code)

        del self._current_incoming_frame

        # Do not let exceptions from the user's callback bubble up any further:
        try:
            if self._on_incoming_frame_complete_cb is not None:
                self._on_incoming_frame_complete_cb(cbdata)
        except BaseException:
            print("Exception in WebSocket on_incoming_frame_complete callback", file=sys.stderr)
            sys.excepthook(*sys.exc_info())
            return False  # close websocket

        return True


def connect(
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
    """Asynchronously establish a client WebSocket connection.

    The `on_connection_setup` callback is invoked once the connection
    has succeeded or failed.

    If successful, a :class:`WebSocket` will be provided in the
    :class:`OnConnectionSetupData`. You should store this WebSocket somewhere,
    so that you can continue using it (the connection will shut down
    if the class is garbage collected).

    The WebSocket will shut down after one of these things occur:
        * You call :meth:`WebSocket.close()`
        * You, or the server, sends a CLOSE frame.
        * The underlying socket shuts down.
        * All references to the WebSocket are dropped,
          causing it to be garbage collected. However, you should NOT
          rely on this behavior. You should call :meth:`~WebSocket.close()` when you are
          done with a healthy WebSocket, to ensure that it shuts down and cleans up.
          It is very easy to accidentally keep a reference around without realizing it.

    Be sure to read about :ref:`authoring-callbacks`.

    Args:
        host: Hostname to connect to.

        port: Port to connect to. If not specified, it defaults to port 443
            when `tls_connection_options` is present, and port 80 otherwise.

        handshake_request: HTTP request for the initial WebSocket handshake.

            The request's method MUST be "GET", and the following headers are
            required::

                Host: <host>
                Upgrade: websocket
                Connection: Upgrade
                Sec-WebSocket-Key: <base64-encoding of 16 random bytes>
                Sec-WebSocket-Version: 13

            You can use :meth:`create_handshake_request()` to make a valid WebSocket
            handshake request, modifying the path and headers to fit your needs,
            and then passing it here.

        bootstrap: Client bootstrap to use when initiating socket connection.
            If not specified, the default singleton is used.

        socket_options: Socket options.
            If not specified, default options are used.

        proxy_options: HTTP Proxy options.
            If not specified, no proxy is used.

        manage_read_window: Set true to manually manage the flow-control read window.
            If false (the default), data arrives as fast as possible.
            See :ref:`flow-control-reading` for a thorough explanation.

        initial_read_window: The initial size of the read window, in bytes.
            This must be set if `manage_read_window` is true,
            otherwise it is ignored.
            See :ref:`flow-control-reading` for a thorough explanation.
            An initial size of 0 will prevent any frames from arriving
            until :meth:`WebSocket.increment_read_window()` is called.

        on_connection_setup: Callback invoked when the connect completes.
            Takes a single :class:`OnConnectionSetupData` argument.

            If successful, :attr:`OnConnectionSetupData.websocket` will be set.
            You should store the :class:`WebSocket` somewhere, so you can
            use it to send data when you're ready.
            The other callbacks will be invoked as events occur,
            until the final `on_connection_shutdown` callback.

            If unsuccessful, :attr:`OnConnectionSetupData.exception` will be set,
            and no further callbacks will be invoked.

            If this callback raises an exception, the connection will shut down.

        on_connection_shutdown: Optional callback, invoked when a connection shuts down.
            Takes a single :class:`OnConnectionShutdownData` argument.

            This callback is never invoked if `on_connection_setup` reported an exception.

        on_incoming_frame_begin: Optional callback, invoked once at the start of each incoming frame.
            Takes a single :class:`OnIncomingFrameBeginData` argument.

            Each `on_incoming_frame_begin` call will be followed by 0+
            `on_incoming_frame_payload` calls, followed by one
            `on_incoming_frame_complete` call.

            The "frame complete" callback is guaranteed to be invoked
            once for each "frame begin" callback, even if the connection
            is lost before the whole frame has been received.

            If this callback raises an exception, the connection will shut down.

        on_incoming_frame_payload: Optional callback, invoked 0+ times as payload data arrives.
            Takes a single :class:`OnIncomingFramePayloadData` argument.

            If `manage_read_window` is on, and this is a "data frame",
            then the read window shrinks accordingly.
            See :ref:`flow-control-reading` for a thorough explanation.

            If this callback raises an exception, the connection will shut down.

        on_incoming_frame_complete: Optional callback, invoked when the WebSocket
            is done processing an incoming frame.
            Takes a single :class:`OnIncomingFrameCompleteData` argument.

            If :attr:`OnIncomingFrameCompleteData.exception` is set,
            then something went wrong processing the frame
            or the connection was lost before the frame could be completed.

            If this callback raises an exception, the connection will shut down.
    """
    if manage_read_window:
        if initial_read_window is None:
            raise ValueError("'initial_read_window' must be set if 'manage_read_window' is enabled")
    else:
        initial_read_window = 0  # value is ignored anyway

    if initial_read_window < 0:
        raise ValueError("'initial_read_window' cannot be negative")

    if port is None:
        port = 0  # C layer uses zero to indicate "defaults please"

    if bootstrap is None:
        bootstrap = ClientBootstrap.get_or_create_static_default()

    if socket_options is None:
        socket_options = SocketOptions()

    core = _WebSocketCore(
        on_connection_setup,
        on_connection_shutdown,
        on_incoming_frame_begin,
        on_incoming_frame_payload,
        on_incoming_frame_complete)

    _awscrt.websocket_client_connect(
        host,
        port,
        handshake_request,
        bootstrap,
        socket_options,
        tls_connection_options,
        proxy_options,
        manage_read_window,
        initial_read_window,
        core)


def create_handshake_request(*, host: str, path: str = '/') -> HttpRequest:
    """Create an HTTP request with all the required fields for a WebSocket handshake.

    The method will be "GET", and the following headers are added::

        Host: <host>
        Upgrade: websocket
        Connection: Upgrade
        Sec-WebSocket-Key: <base64-encoding of 16 random bytes>
        Sec-WebSocket-Version: 13

    You may can add headers, or modify the path, before using this request.

    Args:
        host: Value for "Host" header
        path: Path (and query) string. Defaults to "/".
    """
    http_request_binding, http_headers_binding = _awscrt.websocket_create_handshake_request(host, path)
    return HttpRequest._from_bindings(http_request_binding, http_headers_binding)
