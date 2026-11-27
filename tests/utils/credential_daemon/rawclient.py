# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""A bare JSON-RPC client for poking the fake credential daemon.

This isn't the CLI's credential daemon client. It exists so tests and
developers can drive the fake directly.
"""

import json
import socket


class RawRpcError(Exception):
    def __init__(self, error):
        super().__init__(error.get('message'))
        self.code = error.get('code')
        self.message = error.get('message')
        self.data = error.get('data') or {}

    @property
    def data_code(self):
        return self.data.get('code')


class RawClient:
    def __init__(self, socket_path, timeout=10):
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.settimeout(timeout)
        self._sock.connect(socket_path)
        self._rfile = self._sock.makefile('rb')
        self._next_id = 0
        # Every notifications/progress received, in order.
        self.notifications = []

    def send(self, message):
        self.send_raw(json.dumps(message).encode('utf-8') + b'\n')

    def send_raw(self, data):
        self._sock.sendall(data)

    def read(self):
        line = self._rfile.readline()
        if not line:
            raise EOFError('The credential daemon closed the connection')
        return json.loads(line)

    def request(self, method, params=None):
        """Send a request without waiting for it. Returns its id."""
        self._next_id += 1
        message = {'jsonrpc': '2.0', 'id': self._next_id, 'method': method}
        if params is not None:
            message['params'] = params
        self.send(message)
        return self._next_id

    def call(self, method, params=None, on_notification=None):
        """Call a method and wait for its result.

        ``on_notification(client, params)`` runs for each progress
        notification, so a test can answer prompts with ``respond``.
        """
        request_id = self.request(method, params)
        return self.wait_for(request_id, on_notification)

    def wait_for(self, request_id, on_notification=None):
        while True:
            message = self.read()
            if 'id' not in message:
                self.notifications.append(message['params'])
                if on_notification is not None:
                    on_notification(self, message['params'])
                continue
            if message['id'] != request_id:
                continue
            if 'error' in message:
                raise RawRpcError(message['error'])
            return message['result']

    def respond(self, request_id, **answer):
        """Answer a sign-in prompt (credential/bootstrap/respond)."""
        self.send(
            {
                'jsonrpc': '2.0',
                'method': 'credential/bootstrap/respond',
                'params': dict(answer, request_id=request_id),
            }
        )

    def close(self):
        self._rfile.close()
        self._sock.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()
