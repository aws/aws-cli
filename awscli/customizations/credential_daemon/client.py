# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""The credential daemon client the CLI's commands use."""

from botocore.credential_daemon import CredentialDaemonClient


def command_client():
    """A client for one command run.

    It keeps the socket its first call finds (``pin_socket``), so a command
    that lists and then changes credentials can't act on one daemon's rows
    in another daemon.
    """
    return CredentialDaemonClient(pin_socket=True)
