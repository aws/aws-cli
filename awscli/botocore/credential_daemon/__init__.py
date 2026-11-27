# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Profile rules and a client for the credential daemon.

A profile with ``credential_daemon = <name>`` gets its credentials from
the daemon credential with that name, and from nowhere else.

The credential daemon speaks JSON-RPC 2.0 over a local Unix socket, one JSON
object per line. Credentials are addressed by name.
"""

from botocore.credential_daemon.client import (
    LOGOUT_TIMEOUT,
    SIGN_IN_TIMEOUT,
    CredentialDaemonClient,
)
from botocore.credential_daemon.codesign import (
    CREDENTIAL_DAEMON_CODE_REQUIREMENT,
    CREDENTIAL_DAEMON_PACKAGE_ID,
    CREDENTIAL_DAEMON_TEAM_ID,
    check_code_signature,
    checks_code_signature,
)
from botocore.credential_daemon.config import (
    CLI_TAGS,
    CONFIG_FILE_ONLY_KEYS,
    CREDENTIAL_DAEMON_KEY,
    DAEMON_SOCKET_ENV_VAR,
    KEYS_TAG,
    LOGIN_TAG,
    SSO_TAG,
    credential_daemon_value,
    full_config_with_config_file_keys,
    get_credential_daemon_name,
    is_sso_profile,
    is_sso_profile_without_role,
    is_valid_credential_name,
    profiles_with_config_file_keys,
    tagged_credential_name,
)
from botocore.credential_daemon.discovery import (
    HOME_SOCKET_DIR_NAME,
    HOME_SOCKET_FILE_NAME,
    LINUX_OWN_SOCKET_PATH,
    MACOS_OWN_SOCKET_PATH,
    SHOWN_HOME_SOCKET,
    HomeSocketPath,
    NoSocketPath,
    check_home_socket,
    default_socket_path,
    home_socket_path,
    own_socket_path,
    socket_discovery_notes,
    socket_override,
)
from botocore.credential_daemon.host import Host
from botocore.credential_daemon.messages import (
    INSTALL_COMMAND,
    LINK_COMMAND,
    LINK_REMOVE_COMMAND,
    NO_SOCKET_TO_LINK_HINT,
    START_HINT,
    USE_FILES_HERE_ENV_HINT,
    USE_FILES_HERE_HINT,
    approval_instructions,
    start_hint,
    unavailable_here_message,
)
from botocore.credential_daemon.model import (
    AWS_LOGIN_SOURCE,
    EXPIRED,
    IAM_USER_SOURCE,
    SIGN_IN_REQUIRED,
    SSO_SOURCE,
    CredentialRow,
    LogoutResult,
    SocketChecks,
    Source,
    Status,
    credential_names,
    credential_source,
    credential_status,
    find_credential_row,
    is_logout_unsupported,
)
from botocore.credential_daemon.text import (
    end_sentence,
    strip_control_characters,
)
from botocore.credential_daemon.transport import (
    CONNECT_TIMEOUT,
    DEFAULT_TIMEOUT,
    MAX_MESSAGE_BYTES,
    MAX_REPLY_LINE_BYTES,
    probe_socket,
)
from botocore.credential_daemon.trust import (
    OVERFLOW_UID,
    check_peer,
    check_socket,
    check_socket_folders,
    system_socket_paths,
)
