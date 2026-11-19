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
"""Shared constants and help text for the agent-registry customization."""

SERVICE = 'agent-registry'

# The data plane reads, as commands. Their responses can carry presigned
# download URLs, which are kept out of logs and CLI history.
DATA_PLANE_OPERATIONS = [
    'list-discoverable-registry-records',
    'search-discoverable-registry-records',
    'batch-get-discoverable-registry-record',
]
# The same operations by their API names, as events after the call name them.
DATA_PLANE_API_OPERATIONS = [
    'ListDiscoverableRegistryRecords',
    'SearchDiscoverableRegistryRecords',
    'BatchGetDiscoverableRegistryRecord',
]

# Derived from the model's ``signingName``, matching botocore's convention in
# ``botocore.utils._get_bearer_env_var_name``.
TOKEN_ENV_VAR = 'AWS_BEARER_TOKEN_AGENT_REGISTRY'
# The auth_scheme_preference name of the model's smithy.api#httpBearerAuth.
BEARER_SCHEME = 'httpBearerAuth'
# The signature version botocore chooses for that scheme, whatever the
# token's source.
BEARER_SIGNATURE_VERSION = 'bearer'

PRM_PATH = '/.well-known/oauth-protected-resource/registry/{registry_id}/mcp'
OIDC_METADATA_PATH = '/.well-known/openid-configuration'
HTTP_TIMEOUT = 15
# The most a discovery document or token response is read; anything larger
# is refused rather than held in memory.
MAX_RESPONSE_BYTES = 1024 * 1024

# Identity providers control the error text they send back, and it is echoed
# to the terminal. Longer text is cut off at this many characters.
MAX_PRINTED_TEXT = 300

# Refresh a little early so a token cannot expire mid-flight.
EXPIRY_SKEW_SECONDS = 120

# The listener binds the loopback address only, and the redirect URI names it
# rather than 'localhost', which can resolve to ::1 first and miss an
# IPv4-only listener (RFC 8252, section 7.3). The path is the one the CLI's
# shared listener (AuthCodeFetcher) serves.
CALLBACK_HOST = '127.0.0.1'
CALLBACK_PATH = '/oauth/callback'
# Providers require redirect URIs to be pre-registered exactly, so the port has
# to be predictable rather than ephemeral. Overridable for collisions.
DEFAULT_CALLBACK_PORT = 8484
CALLBACK_PORT_ENV_VAR = 'AWS_AGENT_REGISTRY_CALLBACK_PORT'
DEFAULT_REDIRECT_URI = (
    f'http://{CALLBACK_HOST}:{DEFAULT_CALLBACK_PORT}{CALLBACK_PATH}'
)

# Requesting every advertised scope is wrong: providers reject unknown scopes
# and it grants far more than this flow needs.
WANTED_SCOPES = ('openid', 'profile', 'email', 'offline_access')

# What the registry owner sets up in the identity provider, for the
# --client-id help.
_OWNER_SETUP_DOCS = (
    '<p>The registry owner sets up an app client for the CLI in the identity '
    'provider: a public client with no client secret, the callback URL '
    f'<code>{DEFAULT_REDIRECT_URI}</code> (with the port from '
    f'<code>{CALLBACK_PORT_ENV_VAR}</code> if that is set), the '
    'authorization-code flow, the <code>openid</code> scope, and any scopes '
    'the registry advertises in its Protected Resource Metadata. An Amazon '
    'Cognito user pool also needs a domain.</p>'
)

# The sign-in arguments of list-skills and install-skill.
AUTHORIZER_DOCS = (
    '<p>Authorization mode. Omit this argument, or specify '
    '<code>SIGV4</code>, to sign requests with your AWS credentials. Specify '
    '<code>JWT</code> for a registry configured with a '
    '<code>CUSTOM_JWT</code> authorizer, to send a bearer token from the '
    "registry owner's identity provider instead. The token comes from "
    f'<code>{TOKEN_ENV_VAR}</code> if that is set, and is then sent as is. '
    'Otherwise it comes from the cached sign-in for this registry and '
    'endpoint, refreshed silently when possible. If there is no usable '
    'cached sign-in, you sign in through the browser and the new sign-in is '
    'cached. The CLI requests any scopes the registry advertises in its '
    'Protected Resource Metadata. Remove a cached sign-in with '
    '<code>sign-out</code>.</p>'
)

CLIENT_ID_DOCS = (
    '<p>OAuth client id to sign in with when <code>--authorizer JWT</code> '
    'is used. Protected Resource Metadata does not publish the client id, so '
    'it must be supplied by the registry owner. If omitted, the CLI reuses '
    'the client id of the earlier sign-in to this registry at this endpoint, '
    'if that was with the same identity provider, or prompts for it when '
    'standard input is a terminal. A client id that differs from the cached '
    'sign-in starts a new sign-in.</p>' + _OWNER_SETUP_DOCS
)

NO_BROWSER_DOCS = (
    '<p>Print the sign-in link instead of opening a browser, when '
    '<code>--authorizer JWT</code> has to sign you in, and open it in a '
    'browser yourself. The sign-in still redirects to '
    f'<code>{CALLBACK_HOST}</code> on the machine that runs the CLI. To sign '
    'in with a browser on another machine, connect from that machine with '
    f'<code>ssh -L {DEFAULT_CALLBACK_PORT}:{CALLBACK_HOST}:'
    f'{DEFAULT_CALLBACK_PORT}</code> to the one that runs the CLI.</p>'
)
