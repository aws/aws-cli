# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""Skill commands and interactive JWT sign-in for ``aws agent-registry``.

The customization adds ``list-skills``, which lists the skills a registry
offers and the local agents each is installed for, ``install-skill`` and
``uninstall-skill``, which install a skill record into local agent skills
folders and uninstall it again, and ``sign-out``, which revokes and deletes
cached sign-ins.

A registry may be configured with a custom JWT authorizer, meaning it accepts a
bearer token minted by the customer's own identity provider rather than SigV4.
The CLI can *send* such a token, when the service model declares
``smithy.api#httpBearerAuth``, but botocore has no way to *obtain* one: there
is no OIDC support in the underlying SDK and no token equivalent of
``credential_process``. ``list-skills`` and ``install-skill`` close that
gap for interactive use with ``--authorizer JWT``:

1. Fetch the registry's OAuth Protected Resource Metadata (RFC 9728) to
   discover which authorization server it trusts. This is an unauthenticated
   well-known GET, not a modeled API call.
2. Identify the provider from the issuer and ask for anything discovery cannot
   supply, notably the OAuth client id, which the metadata does not publish.
3. Sign in through a browser using authorization code with PKCE, so the
   password is only ever entered on the provider's own page.
4. Export the token as a bearer credential, then create the client with the
   bearer auth scheme selected in its config, and make the call.

Tokens are cached per endpoint and registry so later commands refresh
silently instead of prompting again. A token already exported as
``AWS_BEARER_TOKEN_AGENT_REGISTRY`` is sent as is.

The generated data plane commands, such as
``list-discoverable-registry-records``, authenticate as botocore makes them:
with the first scheme the service model lists. The model bundled here
declares SigV4 only, so they sign with SigV4. With a model that also
declares ``smithy.api#httpBearerAuth``, such as a model overlay on
``AWS_DATA_PATH``, they send a bearer token when botocore selects that
scheme, because the caller prefers it (``AWS_AUTH_SCHEME_PREFERENCE`` or
``auth_scheme_preference``), with the token botocore finds: one exported as
``AWS_BEARER_TOKEN_AGENT_REGISTRY``, else the profile's IAM Identity Center
(``sso_session``) sign-in. ``list-skills`` and ``install-skill`` without
``--authorizer JWT`` do the same. For every command, a bearer token is kept
off plain HTTP, a request botocore would sign with a bearer token is refused
when TLS certificate verification is skipped, whatever the token's source,
and tokens and presigned download URLs are kept out of ``--debug`` logs and
CLI history.
"""

import functools
import os

from awscli.customizations.agentregistry.constants import (
    DATA_PLANE_API_OPERATIONS,
    DATA_PLANE_OPERATIONS,
    SERVICE,
    TOKEN_ENV_VAR,
)
from awscli.customizations.agentregistry.install_skill import (
    InstallSkillCommand,
)
from awscli.customizations.agentregistry.list_skills import (
    ListSkillsCommand,
)
from awscli.customizations.agentregistry.sign_out import SignOutCommand
from awscli.customizations.agentregistry.uninstall_skill import (
    UninstallSkillCommand,
)
from awscli.customizations.agentregistry.utils import (
    arm_unverified_tls_check,
    hint_sign_out_on_unauthorized,
    redact_logs_and_history,
    require_https,
)


def initialize(cli):
    """The entry point for the agent-registry customization."""
    cli.register(f'building-command-table.{SERVICE}', inject_commands)
    cli.register(f'before-send.{SERVICE}', reject_bearer_over_plain_http)
    # Armed on the session's emitter, which a generated command's client
    # copies when the CLI creates it, after calling-command. For every
    # operation, including any a model overlay adds. Only generated commands
    # emit calling-command; list-skills and install-skill arm their own
    # client.
    cli.register(
        f'calling-command.{SERVICE}',
        functools.partial(arm_unverified_tls_check_on_command, cli),
    )
    for operation in DATA_PLANE_OPERATIONS:
        event = f'calling-command.{SERVICE}.{operation}'
        cli.register(event, redact_data_plane_call)
    for operation in DATA_PLANE_API_OPERATIONS:
        # Emitted before botocore raises an error. Only the commands that
        # sign in print a hint, for their own calls.
        cli.register(
            f'after-call.{SERVICE}.{operation}', hint_sign_out_on_unauthorized
        )


def reject_bearer_over_plain_http(request, **kwargs):
    """Never put a bearer token on a non-https connection.

    Unlike a SigV4 signature, a bearer token is reusable by anyone who sees it.
    The endpoint can come from ``--endpoint-url``, ``AWS_ENDPOINT_URL*`` or the
    config file, so the check runs on the outgoing request itself.
    """
    authorization = request.headers.get('Authorization') or b''
    if isinstance(authorization, str):
        authorization = authorization.encode('utf-8')
    if authorization.startswith(b'Bearer '):
        require_https(request.url, 'registry endpoint')


def arm_unverified_tls_check_on_command(
    event_emitter, parsed_globals=None, **kwargs
):
    """Never send a bearer token over unverified TLS.

    Runs on ``calling-command``, before the client is created. Botocore signs
    with a bearer token when the caller selects the bearer scheme, with a
    token from ``AWS_BEARER_TOKEN_AGENT_REGISTRY`` or an IAM Identity Center
    sign-in, and the token, unlike a SigV4 signature, can be replayed by
    whoever reads it. Only the signer botocore chooses tells which, so with
    the option to skip certificate verification, a ``before-sign`` check is
    registered on ``event_emitter`` that refuses a bearer-signed request
    before the token is put on it. SigV4 calls are left alone. Returns None,
    so the command is never overridden.
    """
    arm_unverified_tls_check(event_emitter, parsed_globals)


def redact_data_plane_call(**kwargs):
    """Keep a generated data plane command's secrets out of logs and history.

    Runs on ``calling-command``, before the client is created. A BatchGet
    response body, which ``--debug`` logs and CLI history records, carries
    presigned download URLs, and a token exported as
    ``AWS_BEARER_TOKEN_AGENT_REGISTRY`` need not look like a JWT to be sent.
    Nothing else is changed: with ``--generate-cli-skeleton`` nothing is sent
    and this only adds redaction. Returns None, so the command is never
    overridden.
    """
    redact_logs_and_history(os.environ.get(TOKEN_ENV_VAR))


def inject_commands(command_table, session, **kwargs):
    command_table['list-skills'] = ListSkillsCommand(session)
    command_table['install-skill'] = InstallSkillCommand(session)
    command_table['uninstall-skill'] = UninstallSkillCommand(session)
    command_table['sign-out'] = SignOutCommand(session)
