"""Network setup helpers for the blackbox tests."""

import socket
import ssl
from collections.abc import Iterator
from contextlib import contextmanager

from localstub.ca import TLSProxyCA


@contextmanager
def refusing_port() -> Iterator[int]:
    """A loopback port that refuses connections until the block exits.

    Linux refuses a connection to a socket that is bound but not listening,
    but macOS drops it, so a client waits for its connect timeout instead.
    The port is the local end of a connection held open for the block:
    nothing listens on it, so both refuse at once, and the kernel gives it to
    no other socket, including a stub server's, before the client connects.
    """
    with socket.create_server(("127.0.0.1", 0)) as listener:
        with socket.create_connection(listener.getsockname()) as held:
            peer, _ = listener.accept()
            with peer:
                yield held.getsockname()[1]


class ClientHelloRecorder(TLSProxyCA):
    """The proxy's CA, recording the server name of every ClientHello.

    OpenSSL calls each issued context's sni_callback as the proxy reads a
    client's ClientHello, so a connection that never carries a request
    still shows the client began TLS with the proxy.
    """

    def __init__(self) -> None:
        super().__init__()
        self.server_names: list[str | None] = []

    def issue_context(self, host: str) -> ssl.SSLContext:
        context = super().issue_context(host)
        context.sni_callback = self.record_hello
        return context

    def record_hello(
        self,
        connection: ssl.SSLObject,
        server_name: str | None,
        context: ssl.SSLContext,
    ) -> None:
        self.server_names.append(server_name)
