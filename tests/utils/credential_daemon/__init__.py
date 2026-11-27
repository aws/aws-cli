# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""A fake credential daemon for tests and local development.

In tests::

    with FakeCredentialDaemon() as fake:
        with RawClient(fake.socket_path) as client:
            client.call('system/health')

By hand::

    scripts/credential-daemon-mock serve
    scripts/credential-daemon-mock call credential/list
"""

from tests.utils.credential_daemon._protocol import (
    ACTIVE,
    DEFAULT_ACCOUNT_ID,
    DEFAULT_IAM_USER_PRINCIPAL,
    DEFAULT_PRINCIPAL,
    DEFAULT_ROLES,
    DEFAULT_START_URL,
    EXPIRED,
    EXPIRING,
    KIND_IAM_USER,
    KIND_LOGIN,
    KIND_SSO,
    LOGIN_METHOD,
    MAX_LINE_BYTES,
    NO_SESSION,
    PROTOCOL_VERSION,
    SIGN_IN_REQUIRED,
    STATUSES,
    identity_credential_name,
)
from tests.utils.credential_daemon.rawclient import RawClient, RawRpcError
from tests.utils.credential_daemon.server import (
    FakeCredentialDaemon,
    default_socket_path,
)
