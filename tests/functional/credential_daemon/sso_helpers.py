# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Helpers shared by the SSO tests that run against the fake credential
daemon."""

from botocore.credential_daemon.client import CredentialDaemonClient

from tests import mock

START_HINT_TEXT = (
    'Start the credential daemon, or install it with \'aws configure '
    'credential-daemon install\', link its socket with \'aws configure '
    'credential-daemon link\', or set AWS_CREDENTIAL_DAEMON_SOCKET.'
)


def no_credential_daemon_calls():
    """Fail on any request to the credential daemon."""
    return mock.patch.object(
        CredentialDaemonClient,
        '_call',
        side_effect=AssertionError('called the credential daemon'),
    )
