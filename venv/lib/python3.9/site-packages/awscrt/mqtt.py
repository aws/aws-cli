"""
MQTT

All network operations in `awscrt.mqtt` are asynchronous.
"""

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0.
import _awscrt
from concurrent.futures import Future
from enum import IntEnum
from inspect import signature
from awscrt import NativeResource
import awscrt.exceptions
from awscrt.http import HttpProxyOptions, HttpRequest
from awscrt.io import ClientBootstrap, ClientTlsContext, SocketOptions
from dataclasses import dataclass
from awscrt.mqtt5 import Client as Mqtt5Client


class QoS(IntEnum):
    """Quality of Service enumeration

    [MQTT-4.3]
    """

    AT_MOST_ONCE = 0
    """QoS 0 - At most once delivery

    The message is delivered according to the capabilities of the underlying network.
    No response is sent by the receiver and no retry is performed by the sender.
    The message arrives at the receiver either once or not at all.
    """

    AT_LEAST_ONCE = 1
    """QoS 1 - At least once delivery

    This quality of service ensures that the message arrives at the receiver at least once.
    """

    EXACTLY_ONCE = 2
    """QoS 2 - Exactly once delivery

    This is the highest quality of service, for use when neither loss nor
    duplication of messages are acceptable. There is an increased overhead
    associated with this quality of service.

    Note that, while this client supports QoS 2, the AWS IoT Core server
    does not support QoS 2 at time of writing (May 2020).
    """

    def to_mqtt5(self):
        from awscrt.mqtt5 import QoS as Mqtt5QoS
        """Convert a Mqtt3 QoS to Mqtt5 QoS

        """
        return Mqtt5QoS(self.value)


def _try_qos(qos_value):
    """Return None if the value cannot be converted to Qos (ex: 0x80 subscribe failure)"""
    try:
        return QoS(qos_value)
    except Exception:
        return None


class ConnectReturnCode(IntEnum):
    """Connect return code enumeration.

    [MQTT-3.2.2.3]
    """

    ACCEPTED = 0
    """Connection Accepted."""

    UNACCEPTABLE_PROTOCOL_VERSION = 1
    """Connection Refused, unacceptable protocol version.

    The Server does not support the level of the MQTT protocol requested by the Client.
    """

    IDENTIFIER_REJECTED = 2
    """Connection Refused, identifier rejected.

    The Client identifier is correct UTF-8 but not allowed by the Server.
    """

    SERVER_UNAVAILABLE = 3
    """Connection Refused, Server unavailable.

    The Network Connection has been made but the MQTT service is unavailable.
    """

    BAD_USERNAME_OR_PASSWORD = 4
    """Connection Refused, bad user name or password.

    The data in the user name or password is malformed.
    """

    NOT_AUTHORIZED = 5
    """Connection Refused, not authorized.

    The Client is not authorized to connect.
    """


class Will:
    """A Will message is published by the server if a client is lost unexpectedly.

    The Will message is stored on the server when a client connects.
    It is published if the client connection is lost without the server
    receiving a DISCONNECT packet.

    [MQTT-3.1.2-8]

    Args:
        topic (str): Topic to publish Will message on.
        qos (QoS): QoS used when publishing the Will message.
        payload (bytes): Content of Will message.
        retain (bool): Whether the Will message is to be retained when it is published.

    Attributes:
        topic (str): Topic to publish Will message on.
        qos (QoS): QoS used when publishing the Will message.
        payload (bytes): Content of Will message.
        retain (bool): Whether the Will message is to be retained when it is published.
    """
    __slots__ = ('topic', 'qos', 'payload', 'retain')

    def __init__(self, topic, qos, payload, retain):
        self.topic = topic
        self.qos = qos
        self.payload = payload
        self.retain = retain


@dataclass
class OnConnectionSuccessData:
    """Dataclass containing data related to a on_connection_success Callback

    Args:
        return_code (ConnectReturnCode): Connect return. code received from the server.
        session_present (bool): True if the connection resumes an existing session.
                                False if new session. Note that the server has forgotten all previous subscriptions
                                if this is False.
                                Subscriptions can be re-established via resubscribe_existing_topics() if the connection was a reconnection.
    """
    return_code: ConnectReturnCode = None
    session_present: bool = False


@dataclass
class OnConnectionFailureData:
    """Dataclass containing data related to a on_connection_failure Callback

    Args:
        error (ConnectReturnCode): Error code with reason for connection failure
    """
    error: awscrt.exceptions.AwsCrtError = None


@dataclass
class OnConnectionClosedData:
    """Dataclass containing data related to a on_connection_closed Callback.
    Currently unused.
    """
    pass


class Client(NativeResource):
    """MQTT client.

    Args:
        bootstrap (Optional [ClientBootstrap]): Client bootstrap to use when initiating new socket connections.
            If None is provided, the default singleton is used.

        tls_ctx (Optional[ClientTlsContext]): TLS context for secure socket connections.
            If None is provided, then an unencrypted connection is used.
    """

    __slots__ = ('tls_ctx')

    def __init__(self, bootstrap=None, tls_ctx=None):
        assert isinstance(bootstrap, ClientBootstrap) or bootstrap is None
        assert tls_ctx is None or isinstance(tls_ctx, ClientTlsContext)

        super().__init__()
        self.tls_ctx = tls_ctx
        if not bootstrap:
            bootstrap = ClientBootstrap.get_or_create_static_default()
        self._binding = _awscrt.mqtt_client_new(bootstrap, tls_ctx)


@dataclass
class OperationStatisticsData:
    """Dataclass containing some simple statistics about the current state of the connection's queue of operations

    Args:
        incomplete_operation_count (int): total number of operations submitted to the connection that have not yet been completed.  Unacked operations are a subset of this.
        incomplete_operation_size (int): total packet size of operations submitted to the connection that have not yet been completed.  Unacked operations are a subset of this.
        unacked_operation_count (int): total number of operations that have been sent to the server and are waiting for a corresponding ACK before they can be completed.
        unacked_operation_size (int): total packet size of operations that have been sent to the server and are waiting for a corresponding ACK before they can be completed.
    """
    incomplete_operation_count: int = 0
    incomplete_operation_size: int = 0
    unacked_operation_count: int = 0
    unacked_operation_size: int = 0


class Connection(NativeResource):
    """MQTT client connection.

    Args:
        client (Client): MQTT client to spawn connection from.

        host_name (str): Server name to connect to.

        port (int): Server port to connect to.

        client_id (str): ID to place in CONNECT packet. Must be unique across all devices/clients.
            If an ID is already in use, the other client will be disconnected.

        clean_session (bool): Whether or not to start a clean session with each reconnect.
            If True, the server will forget all subscriptions with each reconnect.
            Set False to request that the server resume an existing session
            or start a new session that may be resumed after a connection loss.
            The `session_present` bool in the connection callback informs
            whether an existing session was successfully resumed.
            If an existing session is resumed, the server remembers previous subscriptions
            and sends messages (with QoS1 or higher) that were published while the client was offline.

        on_connection_interrupted: Optional callback invoked whenever the MQTT connection is lost.
            The MQTT client will automatically attempt to reconnect.
            The function should take the following arguments return nothing:

                *   `connection` (:class:`Connection`): This MQTT Connection.

                *   `error` (:class:`awscrt.exceptions.AwsCrtError`): Exception which caused connection loss.

                *   `**kwargs` (dict): Forward-compatibility kwargs.

        on_connection_resumed: Optional callback invoked whenever the MQTT connection
            is automatically resumed. Function should take the following arguments and return nothing:

                *   `connection` (:class:`Connection`): This MQTT Connection

                *   `return_code` (:class:`ConnectReturnCode`): Connect return
                    code received from the server.

                *   `session_present` (bool): True if resuming existing session. False if new session.
                    Note that the server has forgotten all previous subscriptions if this is False.
                    Subscriptions can be re-established via resubscribe_existing_topics().

                *   `**kwargs` (dict): Forward-compatibility kwargs.

        on_connection_success: Optional callback invoked whenever the connection successfully connects.
            This callback is invoked for every successful connect and every successful reconnect.

            Function should take the following arguments and return nothing:

                * `connection` (:class:`Connection`): This MQTT Connection

                * `callback_data` (:class:`OnConnectionSuccessData`): The data returned from the connection success.

        on_connection_failure: Optional callback invoked whenever the connection fails to connect.
            This callback is invoked for every failed connect and every failed reconnect.

            Function should take the following arguments and return nothing:

                * `connection` (:class:`Connection`): This MQTT Connection

                * `callback_data` (:class:`OnConnectionFailureData`): The data returned from the connection failure.

        on_connection_closed: Optional callback invoked whenever the connection has been disconnected and shutdown successfully.
            Function should take the following arguments and return nothing:

                * `connection` (:class:`Connection`): This MQTT Connection

                * `callback_data` (:class:`OnConnectionClosedData`): The data returned from the connection close.

        reconnect_min_timeout_secs (int): Minimum time to wait between reconnect attempts.
            Must be <= `reconnect_max_timeout_secs`.
            Wait starts at min and doubles with each attempt until max is reached.

        reconnect_max_timeout_secs (int): Maximum time to wait between reconnect attempts.
            Must be >= `reconnect_min_timeout_secs`.
            Wait starts at min and doubles with each attempt until max is reached.

        keep_alive_secs (int): The keep alive value, in seconds, to send in CONNECT packet.
            A PING will automatically be sent at this interval.
            The server will assume the connection is lost if no PING is received after 1.5X this value.
            This duration must be longer than ping_timeout_ms.

        ping_timeout_ms (int): Milliseconds to wait for ping response before client assumes
            the connection is invalid and attempts to reconnect.
            This duration must be shorter than `keep_alive_secs`.

        protocol_operation_timeout_ms (int): Milliseconds to wait for the response to the operation
            requires response by protocol. Set to zero to disable timeout. Otherwise,
            the operation will fail if no response is received within this amount of time after
            the packet is written to the socket
            It applied to PUBLISH (QoS>0) and UNSUBSCRIBE now.

        will (Will): Will to send with CONNECT packet. The will is
            published by the server when its connection to the client is unexpectedly lost.

        username (str): Username to connect with.

        password (str): Password to connect with.

        socket_options (Optional[awscrt.io.SocketOptions]): Optional socket options.

        use_websocket (bool): If true, connect to MQTT over websockets.

        websocket_proxy_options (Optional[awscrt.http.HttpProxyOptions]):
            Optional proxy options for websocket connections.  Deprecated, use `proxy_options` instead.

        websocket_handshake_transform: Optional function to transform websocket handshake request.
            If provided, function is called each time a websocket connection is attempted.
            The function may modify the HTTP request before it is sent to the server.
            See :class:`WebsocketHandshakeTransformArgs` for more info.
            Function should take the following arguments and return nothing:

                *   `transform_args` (:class:`WebsocketHandshakeTransformArgs`):
                    Contains HTTP request to be transformed. Function must call
                    `transform_args.done()` when complete.

                *   `**kwargs` (dict): Forward-compatibility kwargs.

        proxy_options (Optional[awscrt.http.HttpProxyOptions]):
            Optional proxy options for all connections.
        """

    def __init__(self,
                 client,
                 host_name,
                 port,
                 client_id,
                 clean_session=True,
                 on_connection_interrupted=None,
                 on_connection_resumed=None,
                 reconnect_min_timeout_secs=5,
                 reconnect_max_timeout_secs=60,
                 keep_alive_secs=1200,
                 ping_timeout_ms=3000,
                 protocol_operation_timeout_ms=0,
                 will=None,
                 username=None,
                 password=None,
                 socket_options=None,
                 use_websockets=False,
                 websocket_proxy_options=None,
                 websocket_handshake_transform=None,
                 proxy_options=None,
                 on_connection_success=None,
                 on_connection_failure=None,
                 on_connection_closed=None
                 ):

        assert isinstance(client, Client) or isinstance(client, Mqtt5Client)
        assert callable(on_connection_interrupted) or on_connection_interrupted is None
        assert callable(on_connection_resumed) or on_connection_resumed is None
        assert isinstance(will, Will) or will is None
        assert isinstance(socket_options, SocketOptions) or socket_options is None
        assert isinstance(websocket_proxy_options, HttpProxyOptions) or websocket_proxy_options is None
        assert isinstance(proxy_options, HttpProxyOptions) or proxy_options is None
        assert callable(websocket_handshake_transform) or websocket_handshake_transform is None
        assert callable(on_connection_success) or on_connection_success is None
        assert callable(on_connection_failure) or on_connection_failure is None
        assert callable(on_connection_closed) or on_connection_closed is None

        if reconnect_min_timeout_secs > reconnect_max_timeout_secs:
            raise ValueError("'reconnect_min_timeout_secs' cannot exceed 'reconnect_max_timeout_secs'")

        if keep_alive_secs * 1000 <= ping_timeout_ms:
            raise ValueError("'keep_alive_secs' duration must be longer than 'ping_timeout_ms'")

        if proxy_options and websocket_proxy_options:
            raise ValueError("'websocket_proxy_options' has been deprecated in favor of 'proxy_options'.  "
                             "Both parameters may not be set.")

        super().__init__()

        # init-only
        self.client = client
        self._client_version = 5 if isinstance(client, Mqtt5Client) else 3
        self._on_connection_interrupted_cb = on_connection_interrupted
        self._on_connection_resumed_cb = on_connection_resumed
        self._use_websockets = use_websockets
        self._ws_handshake_transform_cb = websocket_handshake_transform
        self._on_connection_success_cb = on_connection_success
        self._on_connection_failure_cb = on_connection_failure
        self._on_connection_closed_cb = on_connection_closed

        # may be changed at runtime, take effect the the next time connect/reconnect occurs
        self.client_id = client_id
        self.host_name = host_name
        self.port = port
        self.clean_session = clean_session
        self.reconnect_min_timeout_secs = reconnect_min_timeout_secs
        self.reconnect_max_timeout_secs = reconnect_max_timeout_secs
        self.keep_alive_secs = keep_alive_secs
        self.ping_timeout_ms = ping_timeout_ms
        self.protocol_operation_timeout_ms = protocol_operation_timeout_ms
        self.will = will
        self.username = username
        self.password = password
        self.socket_options = socket_options if socket_options else SocketOptions()
        self.proxy_options = proxy_options if proxy_options else websocket_proxy_options

        self._binding = _awscrt.mqtt_client_connection_new(
            self,
            client,
            use_websockets,
            self._client_version
        )

    def _check_uses_old_message_callback_signature(self, callback):
        # The callback used to have fewer args. Passing only those args, if it
        # only has two args and no forward-compatibility to cover case where
        # user function failed to take forward-compatibility **kwargs.

        callback_sig = signature(callback)
        try:
            # try new signature
            callback_sig.bind(topic='topic', payload='payload', dup=True, qos=QoS(1), retain=True)
            return False
        except TypeError:
            # try old signature
            callback_sig.bind(topic='topic', payload='payload')
            return True

    def _on_connection_interrupted(self, error_code):
        if self._on_connection_interrupted_cb:
            self._on_connection_interrupted_cb(connection=self, error=awscrt.exceptions.from_code(error_code))

    def _on_connection_resumed(self, return_code, session_present):
        if self._on_connection_resumed_cb:
            self._on_connection_resumed_cb(
                connection=self,
                return_code=ConnectReturnCode(return_code),
                session_present=session_present)

    def _ws_handshake_transform(self, http_request_binding, http_headers_binding, native_userdata):
        if self._ws_handshake_transform_cb is None:
            _awscrt.mqtt_ws_handshake_transform_complete(None, native_userdata, 0)
            return

        def _on_complete(f):
            error_code = 0
            hs_exception = f.exception()
            if isinstance(hs_exception, awscrt.exceptions.AwsCrtError):
                error_code = hs_exception.code
            _awscrt.mqtt_ws_handshake_transform_complete(f.exception(), native_userdata, error_code)

        future = Future()
        future.add_done_callback(_on_complete)
        http_request = HttpRequest._from_bindings(http_request_binding, http_headers_binding)
        transform_args = WebsocketHandshakeTransformArgs(self, http_request, future)
        try:
            self._ws_handshake_transform_cb(transform_args=transform_args)
        except Exception as e:
            # Call set_done() if user failed to do so before uncaught exception was raised,
            # there's a chance the callback wasn't callable and user has no idea we tried to hand them the baton.
            if not future.done():
                transform_args.set_done(e)

    def _on_connection_closed(self):
        if self:
            if self._on_connection_closed_cb:
                data = OnConnectionClosedData()
                self._on_connection_closed_cb(connection=self, callback_data=data)

    def _on_connection_success(self, return_code, session_present):
        if self:
            if self._on_connection_success_cb:
                data = OnConnectionSuccessData(
                    return_code=ConnectReturnCode(return_code),
                    session_present=session_present)
                self._on_connection_success_cb(connection=self, callback_data=data)

    def _on_connection_failure(self, error_code):
        if self:
            if self._on_connection_failure_cb:
                data = OnConnectionFailureData(error=awscrt.exceptions.from_code(error_code))
                self._on_connection_failure_cb(connection=self, callback_data=data)

    def connect(self):
        """Open the actual connection to the server (async).

        Returns:
            concurrent.futures.Future: Future which completes when connection succeeds or fails.
            If connection fails, Future will contain an exception.
            If connection succeeds, Future will contain a dict with the following members:

            * ['session_present'] (bool): is True if resuming existing session and False if new session.
        """
        future = Future()

        def on_connect(error_code, return_code, session_present):
            if return_code:
                future.set_exception(Exception(ConnectReturnCode(return_code)))
            elif error_code:
                future.set_exception(awscrt.exceptions.from_code(error_code))
            else:
                future.set_result(dict(session_present=session_present))

        try:
            _awscrt.mqtt_client_connection_connect(
                self._binding,
                self.client_id,
                self.host_name,
                self.port,
                self.socket_options,
                self.client.tls_ctx,
                self.reconnect_min_timeout_secs,
                self.reconnect_max_timeout_secs,
                self.keep_alive_secs,
                self.ping_timeout_ms,
                self.protocol_operation_timeout_ms,
                self.will,
                self.username,
                self.password,
                self.clean_session,
                on_connect,
                self.proxy_options
            )

        except Exception as e:
            future.set_exception(e)

        return future

    def reconnect(self):
        """DEPRECATED.

        awscrt.mqtt.ClientConnection automatically reconnects.
        To cease reconnect attempts, call disconnect().
        To resume the connection, call connect().
        """
        future = Future()

        def on_connect(error_code, return_code, session_present):
            if return_code:
                future.set_exception(Exception(ConnectReturnCode(return_code)))
            elif error_code:
                future.set_exception(awscrt.exceptions.from_code(error_code))
            else:
                future.set_result(dict(session_present=session_present))

        try:
            _awscrt.mqtt_client_connection_reconnect(self._binding, on_connect)
        except Exception as e:
            future.set_exception(e)

        return future

    def disconnect(self):
        """Close the connection (async).

        Returns:
            concurrent.futures.Future: Future which completes when the connection is closed.
            The future will contain an empty dict.
        """

        future = Future()

        def on_disconnect():
            future.set_result(dict())

        try:
            _awscrt.mqtt_client_connection_disconnect(self._binding, on_disconnect)

        except Exception as e:
            future.set_exception(e)

        return future

    def subscribe(self, topic, qos, callback=None):
        """Subscribe to a topic filter (async).

        The client sends a SUBSCRIBE packet and the server responds with a SUBACK.

        subscribe() may be called while the device is offline, though the async
        operation cannot complete successfully until the connection resumes.

        Once subscribed, `callback` is invoked each time a message matching
        the `topic` is received. It is possible for such messages to arrive before
        the SUBACK is received.

        Args:
            topic (str): Subscribe to this topic filter, which may include wildcards.
            qos (QoS): Maximum requested QoS that server may use when sending messages to the client.
                The server may grant a lower QoS in the SUBACK (see returned Future)
            callback: Optional callback invoked when message received.
                Function should take the following arguments and return nothing:

                    *   `topic` (str): Topic receiving message.

                    *   `payload` (bytes): Payload of message.

                    *   `dup` (bool): DUP flag. If True, this might be re-delivery
                        of an earlier attempt to send the message.

                    *   `qos` (:class:`QoS`): Quality of Service used to deliver the message.

                    *   `retain` (bool): Retain flag. If True, the message was sent
                        as a result of a new subscription being made by the client.

                    *   `**kwargs` (dict): Forward-compatibility kwargs.

        Returns:
            Tuple[concurrent.futures.Future, int]: Tuple containing a Future and
            the ID of the SUBSCRIBE packet. The Future completes when a
            SUBACK is received from the server. If successful, the Future will
            contain a dict with the following members:

                *   ['packet_id'] (int): ID of the SUBSCRIBE packet being acknowledged.

                *   ['topic'] (str): Topic filter of the SUBSCRIBE packet being acknowledged.

                *   ['qos'] (:class:`QoS`): Maximum QoS that was granted by the server.
                    This may be lower than the requested QoS.

            If unsuccessful, the Future contains an exception. The exception
            will be a :class:`SubscribeError` if a SUBACK was received
            in which the server rejected the subscription. Other exception
            types indicate other errors with the operation.
        """

        future = Future()
        packet_id = 0

        if callback:
            uses_old_signature = self._check_uses_old_message_callback_signature(callback)

            def callback_wrapper(topic, payload, dup, qos, retain):
                if uses_old_signature:
                    callback(topic=topic, payload=payload)
                else:
                    callback(topic=topic, payload=payload, dup=dup, qos=QoS(qos), retain=retain)

        else:
            callback_wrapper = None

        def suback(packet_id, topic, qos, error_code):
            if error_code:
                future.set_exception(awscrt.exceptions.from_code(error_code))
            else:
                qos = _try_qos(qos)
                if qos is None:
                    future.set_exception(SubscribeError(topic))
                else:
                    future.set_result(dict(
                        packet_id=packet_id,
                        topic=topic,
                        qos=qos,
                    ))

        try:
            assert callable(callback) or callback is None
            from awscrt.mqtt5 import QoS as Mqtt5QoS
            if (isinstance(qos, Mqtt5QoS)):
                qos = qos.to_mqtt3()
            assert isinstance(qos, QoS)
            packet_id = _awscrt.mqtt_client_connection_subscribe(
                self._binding, topic, qos.value, callback_wrapper, suback)
        except Exception as e:
            future.set_exception(e)

        return future, packet_id

    def on_message(self, callback):
        """Set callback to be invoked when ANY message is received.

        callback: Callback to invoke when message received, or None to disable.
            Function should take the following arguments and return nothing:

                *   `topic` (str): Topic receiving message.

                *   `payload` (bytes): Payload of message.

                *   `dup` (bool): DUP flag. If True, this might be re-delivery
                    of an earlier attempt to send the message.

                *   `qos` (:class:`QoS`): Quality of Service used to deliver the message.

                *   `retain` (bool): Retain flag. If True, the message was sent
                    as a result of a new subscription being made by the client.

                *   `**kwargs` (dict): Forward-compatibility kwargs.
        """
        assert callable(callback) or callback is None

        if callback:

            uses_old_signature = self._check_uses_old_message_callback_signature(callback)

            def callback_wrapper(topic, payload, dup, qos, retain):
                if uses_old_signature:
                    callback(topic=topic, payload=payload)
                else:
                    callback(topic=topic, payload=payload, dup=dup, qos=QoS(qos), retain=retain)

        else:
            callback_wrapper = None

        _awscrt.mqtt_client_connection_on_message(self._binding, callback_wrapper)

    def unsubscribe(self, topic):
        """Unsubscribe from a topic filter (async).

        The client sends an UNSUBSCRIBE packet, and the server responds with an UNSUBACK.

        Args:
            topic (str): Unsubscribe from this topic filter.

        Returns:
            Tuple[concurrent.futures.Future, int]: Tuple containing a Future and
            the ID of the UNSUBSCRIBE packet. The Future completes when an
            UNSUBACK is received from the server. If successful, the Future
            will contain a dict with the following members:

            * ['packet_id'] (int): ID of the UNSUBSCRIBE packet being acknowledged.
        """
        future = Future()
        packet_id = 0

        def unsuback(packet_id, error_code):
            if error_code != 0:
                future.set_exception(awscrt.exceptions.from_code(error_code))
            else:
                future.set_result(dict(packet_id=packet_id))

        try:
            packet_id = _awscrt.mqtt_client_connection_unsubscribe(self._binding, topic, unsuback)

        except Exception as e:
            future.set_exception(e)

        return future, packet_id

    def resubscribe_existing_topics(self):
        """
        Subscribe again to all current topics.

        This is to help when resuming a connection with a clean session.

        **Important**: Currently the resubscribe function does not take the AWS IoT Core maximum subscriptions
        per subscribe request quota into account. If the client has more subscriptions than the maximum,
        resubscribing must be done manually using the `subscribe()` function for each desired topic
        filter. The client will be disconnected by AWS IoT Core if the resubscribe exceeds the subscriptions
        per subscribe request quota.

        The AWS IoT Core maximum subscriptions per subscribe request quota is listed at the following URL:
        https://docs.aws.amazon.com/general/latest/gr/iot-core.html#genref_max_subscriptions_per_subscribe_request

        Returns:
            Tuple[concurrent.futures.Future, int]: Tuple containing a Future and
            the ID of the SUBSCRIBE packet. The Future completes when a SUBACK
            is received from the server. If successful, the Future will contain
            a dict with the following members:

            *   ['packet_id']: ID of the SUBSCRIBE packet being acknowledged,
                or None if there were no topics to resubscribe to.

            *   ['topics']: A list of (topic, qos) tuples, where qos will be
                None if the topic failed to resubscribe. If there were no topics
                to resubscribe to, then the list will be empty.
        """
        packet_id = 0
        future = Future()

        def on_suback(packet_id, topic_qos_tuples, error_code):
            if error_code:
                future.set_exception(awscrt.exceptions.from_code(error_code))
            else:
                future.set_result(dict(
                    packet_id=packet_id,
                    topics=[(topic, _try_qos(qos)) for (topic, qos) in topic_qos_tuples],
                ))

        try:
            packet_id = _awscrt.mqtt_client_connection_resubscribe_existing_topics(self._binding, on_suback)
            if packet_id is None:
                # There were no topics to resubscribe to.
                future.set_result(dict(packet_id=None, topics=[]))

        except Exception as e:
            future.set_exception(e)

        return future, packet_id

    def publish(self, topic, payload, qos, retain=False):
        """Publish message (async).

        If the device is offline, the PUBLISH packet will be sent once the connection resumes.

        Args:
            topic (str): Topic name.
            payload (Union[str, bytes, bytearray]): Contents of message.
            qos (QoS): Quality of Service for delivering this message.
            retain (bool): If True, the server will store the message and its QoS
                so that it can be delivered to future subscribers whose subscriptions
                match its topic name.

        Returns:
            Tuple[concurrent.futures.Future, int]: Tuple containing a Future and
            the ID of the PUBLISH packet. The QoS determines when the Future completes:

            *   For QoS 0, completes as soon as the packet is sent.
            *   For QoS 1, completes when PUBACK is received.
            *   For QoS 2, completes when PUBCOMP is received.

            If successful, the Future will contain a dict with the following members:

            *   ['packet_id'] (int): ID of the PUBLISH packet that is complete.
        """
        future = Future()
        packet_id = 0

        def puback(packet_id, error_code):
            if error_code != 0:
                future.set_exception(awscrt.exceptions.from_code(error_code))
            else:
                future.set_result(dict(packet_id=packet_id))

        try:
            from awscrt.mqtt5 import QoS as Mqtt5QoS
            if (isinstance(qos, Mqtt5QoS)):
                qos = qos.to_mqtt3()
            assert isinstance(qos, QoS)
            packet_id = _awscrt.mqtt_client_connection_publish(self._binding, topic, payload, qos.value, retain, puback)
        except Exception as e:
            future.set_exception(e)

        return future, packet_id

    def get_stats(self):
        """Queries the connection's internal statistics for incomplete operations.

        Returns:
            The (:class:`OperationStatisticsData`) containing the statistics
        """

        result = _awscrt.mqtt_client_connection_get_stats(self._binding)
        return OperationStatisticsData(result[0], result[1], result[2], result[3])


class WebsocketHandshakeTransformArgs:
    """
    Argument to a "websocket_handshake_transform" function.

    A websocket_handshake_transform function has signature:
    ``fn(transform_args: WebsocketHandshakeTransformArgs, **kwargs) -> None``

    The function implementer may modify `transform_args.http_request` as desired.
    They MUST call `transform_args.set_done()` when complete, passing an
    exception if something went wrong. Failure to call `set_done()`
    will hang the application.

    The implementer may do asynchronous work before calling `transform_args.set_done()`,
    they are not required to call `set_done()` within the scope of the transform function.
    An example of async work would be to fetch credentials from another service,
    sign the request headers, and finally call `set_done()` to mark the transform complete.

    The default websocket handshake request uses path "/mqtt".
    All required headers are present,
    plus the optional header "Sec-WebSocket-Protocol: mqtt".

    Args:
        mqtt_connection (Connection): Connection this handshake is for.
        http_request (awscrt.http.HttpRequest): HTTP request for this handshake.
        done_future (concurrent.futures.Future): Future to complete when the
            :meth:`set_done()` is called. It will contain None if successful,
            or an exception will be set.

    Attributes:
        mqtt_connection (Connection): Connection this handshake is for.
        http_request (awscrt.http.HttpRequest): HTTP request for this handshake.
    """

    def __init__(self, mqtt_connection, http_request, done_future):
        self.mqtt_connection = mqtt_connection
        self.http_request = http_request
        self._done_future = done_future

    def set_done(self, exception=None):
        """
        Mark the transformation complete.
        If exception is passed in, the handshake is canceled.
        """
        if exception is None:
            self._done_future.set_result(None)
        else:
            self._done_future.set_exception(exception)


class SubscribeError(Exception):
    """
    Subscription rejected by server.
    """
    pass
