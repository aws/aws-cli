# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""A hint to install the credential daemon.

Before the credential daemon is installed, ``aws login`` says, in a
terminal, how to install it when it writes a session to a file, and
``aws configure`` when it writes access keys to one::

    note: this session is stored unencrypted in ~/.aws/login/cache. A
    developer preview of the AWS credential daemon is available (not for
    production use): aws configure credential-daemon install

``credential_storage = file`` on the profile, or
``AWS_CREDENTIAL_STORAGE = file``, turns it off, and so does a machine that
``install`` has no release for. Commands that only use credentials, such as
API calls, never show it.

This module loads with the commands that show it, so the install command's
module, which is large, loads only when the check runs.
"""

import logging
import sys

from botocore.credential_daemon import NoSocketPath, default_socket_path

from awscli.customizations.credential_daemon.messages import (
    display_path,
    quoted_names,
)
from awscli.customizations.credential_daemon.storage.chooser import (
    known_decision,
)
from awscli.customizations.credential_daemon.storage.policy import (
    DecisionSource,
)
from awscli.customizations.credential_daemon.storage.presence import (
    socket_path_present,
)
from awscli.customizations.utils import uni_print
from awscli.utils import is_stderr_a_tty, is_stdin_a_tty

LOG = logging.getLogger(__name__)

INSTALL_COMMAND = 'aws configure credential-daemon install'


def _in_terminal():
    return is_stdin_a_tty() and is_stderr_a_tty()


def print_session_install_hint(storage, cache_dir):
    """Once a sign-in has saved its session in ``cache_dir``, say how to
    install the credential daemon, if it isn't installed.

    ``storage`` is the sign-in's ``StorageChoice``. Only files used because
    nothing chose otherwise count: a customer or admin who chose files gets
    nothing.
    """
    try:
        if (
            storage.source is not DecisionSource.DEFAULT
            or not _in_terminal()
            or not _install_hint_applies()
        ):
            return
        _print_install_hint(
            f'this session is stored unencrypted in {display_path(cache_dir)}'
        )
    except Exception as e:
        # A hint must never break the command.
        LOG.debug('Install hint failed: %s', e, exc_info=True)


def print_keys_install_hint(session, profile_name, path, choice=None):
    """Once aws configure has written long-term IAM access keys for
    ``profile_name`` to ``path``, say how to install the credential daemon,
    if it isn't installed.

    ``choice`` is the storage question's ``StorageChoice`` for a new
    profile; other profiles use what they have. As for a session, only
    files used because nothing chose otherwise count.
    """
    try:
        if choice is None:
            choice = known_decision(session, profile_name)
        if (
            choice.source not in (None, DecisionSource.DEFAULT)
            or not _in_terminal()
            or not _install_hint_applies()
        ):
            return
        # "for new profiles": installing doesn't move these keys, because
        # aws configure stores keys in the credential daemon only for a new
        # profile. For example, [ci] keeps writing ~/.aws/credentials after
        # the install.
        _print_install_hint(
            f'the IAM access keys for {quoted_names([profile_name])} are '
            f'stored unencrypted in {display_path(path)}',
            for_new_profiles=True,
        )
    except Exception as e:
        # A hint must never break the command.
        LOG.debug('Install hint failed: %s', e, exc_info=True)


def _install_hint_applies():
    from awscli.customizations.configure.credentialdaemon import (
        install_supported,
    )

    return install_supported() and not _credential_daemon_is_installed()


def _print_install_hint(what, for_new_profiles=False):
    # Says it's a developer preview and not for production use, like the
    # notice install prints, but leaves out the docs link to stay one line.
    available = (
        'available for new profiles' if for_new_profiles else 'available'
    )
    uni_print(
        f'note: {what}. A developer preview of the AWS credential daemon '
        f'is {available} (not for production use): {INSTALL_COMMAND}\n',
        sys.stderr,
    )


def _credential_daemon_is_installed():
    """Whether anything is at the socket the CLI would dial. Something
    there that isn't running is covered by the messages that dial it."""
    path = default_socket_path()
    if not path or isinstance(path, NoSocketPath):
        return False
    # A link to nothing is what an uninstall leaves for other users, or a
    # container that mounts ~/.aws but not the socket.
    return socket_path_present(path)
