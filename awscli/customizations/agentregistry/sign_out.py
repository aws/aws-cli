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
"""Revoke and delete cached ``--authorizer JWT`` sign-ins.

Deleting a cache entry alone leaves its refresh token valid at the identity
provider, so a copy of the cache would keep working. Each entry's refresh
token is therefore revoked first (RFC 7009) where the provider advertised a
revocation endpoint. If the revocation request fails, the entry is deleted
all the same, so this machine is signed out, but its refresh token is kept
with the cache's pending revocations: it is still valid, and without it
nothing could revoke it later. Every later sign-out for the registry retries
those revocations first, and fails while any of them does. No AWS
credentials and no AWS client are involved.
"""

import os
import urllib.error

from awscli.customizations.agentregistry import cache
from awscli.customizations.agentregistry.constants import MAX_PRINTED_TEXT
from awscli.customizations.agentregistry.utils import (
    AgentRegistryJWTError,
    bare_registry_id,
    comparable_endpoint,
    http_post_form,
    printable,
    read_error_body,
    refuse_endpoint_query,
    require_https,
    resolve_ca_bundle,
    resolve_data_plane_endpoint,
    write_status,
)
from awscli.customizations.commands import BasicCommand
from awscli.customizations.exceptions import ParamValidationError

# Enough bytes for MAX_PRINTED_TEXT characters of UTF-8.
_ERROR_BODY_BYTES = 4 * MAX_PRINTED_TEXT


def _not_revocable(entry):
    """Why the entry's refresh token cannot be revoked, or None if it can."""
    endpoint = entry.get('revocationEndpoint')
    if not entry.get('refreshToken'):
        return 'there is no refresh token'
    if not isinstance(endpoint, str) or not endpoint:
        return 'the identity provider does not advertise a revocation endpoint'
    return None


def _revoke(entry, ca_bundle):
    """Revoke the refresh token of an entry, or of a token kept for retry.

    Returns why the request failed, or None.
    """
    try:
        # https only, no redirects, and the CLI's CA bundle, like every
        # other request that carries a token.
        http_post_form(
            entry['revocationEndpoint'],
            {
                'token': entry['refreshToken'],
                'token_type_hint': 'refresh_token',
                'client_id': entry.get('clientId') or '',
            },
            ca_bundle=ca_bundle,
            expect_json=False,
        )
    except urllib.error.HTTPError as e:
        # The provider chooses the body; read only as much as is shown.
        body = printable(read_error_body(e, _ERROR_BODY_BYTES))
        detail = f': {body}' if body else ''
        return f'HTTP {e.code} from the identity provider{detail}'
    except urllib.error.URLError as e:
        return printable(e.reason) or type(e).__name__
    except Exception as e:
        return printable(e) or type(e).__name__
    return None


def _label(entry):
    """``Registry R at E``, for the result lines of an entry or kept token."""
    return (
        f'Registry {printable(entry.get("registryId"))} at '
        f'{printable(entry.get("endpoint"))}'
    )


def _retry_advice(entry):
    return (
        'run aws agent-registry sign-out --registry-id '
        f'{printable(entry.get("registryId"))} again'
    )


def _named_for(path, registry_id):
    """True if a pending-revocation file is named for ``registry_id``.

    At any endpoint: an endpoint URL written another way would otherwise
    turn the registry's unrevoked token into someone else's warning.
    """
    return cache.pending_revocation_registry(path) == registry_id


def _report_unreadable(path, problem, warning=False):
    """Report a file of kept refresh tokens that can't be read or placed."""
    write_status(
        f'{"Warning: could" if warning else "Could"} not read the refresh '
        f'tokens kept for revocation in {path} ({printable(problem)}). Left '
        f'it in place: check it, and delete it once its refresh tokens are '
        f'revoked or have expired.'
    )


class SignOutCommand(BasicCommand):
    """Remove cached sign-ins, revoking their refresh tokens first."""

    NAME = 'sign-out'
    DESCRIPTION = (
        'Signs out of registries that use a custom JWT authorizer. For each '
        'cached ``--authorizer JWT`` sign-in, the command revokes the refresh '
        'token at the identity provider and then deletes the sign-in from the '
        'token cache in ``~/.aws/agent-registry/cache``.\n\n'
        'If the sign-in has no refresh token, or the identity provider does '
        'not advertise a revocation endpoint, the command deletes the '
        'sign-in, reports why it did not revoke the refresh token, and '
        'succeeds. If a revocation request fails, the command still deletes '
        'the sign-in, so later commands sign in again, but keeps the refresh '
        'token in ``~/.aws/agent-registry/cache/pending-revocation`` and '
        'exits with status 1. The CLI never signs in or refreshes with a kept '
        'refresh token. Each later ``sign-out`` for the registry first '
        'retries the revocations kept for it, removes each refresh token it '
        'revokes, and exits with status 1 if it cannot revoke one. If the '
        'command cannot keep the refresh token, it leaves the sign-in in '
        'place so that a later ``sign-out`` can retry the revocation. With '
        '``--all``, the command retries every kept revocation, signs out of '
        'every registry, and exits with status 1 if any revocation fails. '
        'The command never deletes a file of kept refresh tokens that it '
        "cannot read, or whose contents don't match its name, and reports it "
        'instead. Such a file makes ``--all`` exit with status 1, and makes '
        '``--registry-id`` exit with status 1 if the file is named for that '
        'registry, at any endpoint, even with ``--endpoint-url``. For any '
        'other such file, ``--registry-id`` only warns. The command does not '
        'affect a token that you export as '
        '``AWS_BEARER_TOKEN_AGENT_REGISTRY``.\n\n'
        'This command sends no requests to AWS and needs no AWS credentials.'
    )
    ARG_TABLE = [
        {
            'name': 'registry-id',
            'help_text': (
                'The id or ARN of the registry to sign out of. The command '
                'retries every revocation kept for the registry and removes '
                'every cached sign-in for it, whatever the endpoint. With '
                '<code>--endpoint-url</code>, it acts only on the endpoint '
                'that the URL resolves to. Specify either this or '
                '<code>--all</code>.'
            ),
        },
        {
            'name': 'all',
            'action': 'store_true',
            'help_text': (
                'Retry every kept revocation, sign out of every registry, and '
                'delete any cache file that an unfinished write left behind. '
                'Specify either this or <code>--registry-id</code>.'
            ),
        },
    ]

    def _run_main(self, parsed_args, parsed_globals):
        if bool(parsed_args.registry_id) == bool(parsed_args.all):
            raise ParamValidationError(
                'Specify exactly one of --registry-id and --all.'
            )
        if parsed_args.all:
            pending = cache.list_pending_revocations()
            entries = cache.list_entries()
            # Not entries, but they can hold tokens: the temp files of
            # unfinished writes.
            others = [
                (path, 'the unfinished cache write')
                for path in cache.list_temp_files()
            ]
            if not pending and not entries and not others:
                write_status('Not signed in.')
                return 0
        else:
            registry_id = bare_registry_id(parsed_args.registry_id)
            endpoint = self._endpoint(parsed_globals)
            pending, elsewhere = self._pending_for(registry_id, endpoint)
            entries = self._entries_for(registry_id, endpoint)
            others = []
            # Not this registry's, as far as can be told, so a warning: a
            # damaged file must not make every other sign-out fail.
            for path, problem in elsewhere:
                _report_unreadable(path, problem, warning=True)
            if not pending and not entries:
                where = f' at {endpoint}' if endpoint else ''
                write_status(f'No cached sign-in for {registry_id}{where}.')
                return 0

        ca_bundle = resolve_ca_bundle(self._session, parsed_globals)
        # The revocations that earlier sign-outs could not make come first.
        results = [
            self._retry(path, document, problem, ca_bundle)
            for path, document, problem in pending
        ]
        results += [
            self._sign_out(path, entry, ca_bundle) for path, entry in entries
        ]
        results += [self._remove(path, what) for path, what in others]
        return 0 if all(results) else 1

    def _endpoint(self, parsed_globals):
        """The endpoint ``--endpoint-url`` resolves to, or None without it.

        Resolved as for the API call, as the cached entries were. That builds
        an unsigned client but sends nothing and needs no credentials.
        """
        endpoint_url = getattr(parsed_globals, 'endpoint_url', None)
        if not endpoint_url:
            return None
        region = getattr(
            parsed_globals, 'region', None
        ) or self._session.get_config_variable('region')
        if not region:
            # Botocore needs a region to build the client, but the endpoint
            # rules return an --endpoint-url as given.
            refuse_endpoint_query(endpoint_url, parsed_globals)
            return require_https(endpoint_url, 'registry endpoint').rstrip('/')
        return resolve_data_plane_endpoint(
            self._session, parsed_globals, region
        )

    def _entries_for(self, registry_id, endpoint):
        wanted = comparable_endpoint(endpoint) if endpoint else None
        return [
            (path, entry)
            for path, entry in cache.list_entries()
            if entry is not None
            and entry.get('registryId') == registry_id
            and (
                wanted is None
                or comparable_endpoint(entry.get('endpoint')) == wanted
            )
        ]

    def _pending_for(self, registry_id, endpoint):
        """The registry's pending revocations, and others that can't be read.

        Returns ``(pending, elsewhere)``. ``pending`` is ``(path, document,
        problem)`` for each of the registry's files: those that can be read,
        and those that can't, or whose contents don't match their name, but
        whose name is the registry's, whatever ``endpoint`` is. ``elsewhere``
        is ``(path, problem)`` for each other file that can't be read or
        placed, which may hold any registry's tokens.
        """
        wanted = comparable_endpoint(endpoint) if endpoint else None
        pending = []
        elsewhere = []
        for path, document, problem in cache.list_pending_revocations():
            if document is not None:
                if document['registryId'] == registry_id and (
                    wanted is None
                    or comparable_endpoint(document['endpoint']) == wanted
                ):
                    pending.append((path, document, problem))
            elif _named_for(path, registry_id):
                pending.append((path, document, problem))
            else:
                elsewhere.append((path, problem))
        return pending, elsewhere

    def _retry(self, path, document, problem, ca_bundle):
        """Retry the revocations kept in one file; report them, return success.

        A token that is revoked is removed from the file; one that is not
        stays. A file that cannot be read is left as it is, and is a
        failure.
        """
        if document is None:
            _report_unreadable(path, problem)
            return False
        label = _label(document)
        revoked = []
        for token in document['tokens']:
            reason = _revoke(token, ca_bundle)
            if reason is None:
                revoked.append(token['refreshToken'])
                write_status(
                    f'{label}: revoked a refresh token that an earlier '
                    f'sign-out could not revoke.'
                )
            else:
                write_status(
                    f'{label}: could not revoke a refresh token that an '
                    f'earlier sign-out could not revoke either ({reason}). '
                    f'Kept it so the revocation can be retried: '
                    f'{_retry_advice(document)}.'
                )
        if revoked:
            try:
                cache.remove_pending_revocations(path, revoked)
            except (OSError, AgentRegistryJWTError) as e:
                write_status(
                    f'{label}: could not remove the revoked refresh tokens '
                    f'from {path}: {printable(e)}'
                )
                return False
        return len(revoked) == len(document['tokens'])

    def _remove(self, path, what):
        try:
            os.remove(path)
        except FileNotFoundError:
            return True
        except OSError as e:
            write_status(f'Could not remove {what} {path}: {printable(e)}')
            return False
        write_status(f'Removed {what} {path}.')
        return True

    def _sign_out(self, path, entry, ca_bundle):
        """Revoke and delete one entry; report it and return success.

        The entry is deleted, so this machine is signed out, unless its
        refresh token could be neither revoked nor kept for a retry. A
        revocation request that failed is still a failure: the refresh token
        remains valid until a later sign-out revokes it.
        """
        if entry is None:
            # Unreadable, so there is nothing to revoke.
            label = 'Unreadable cache entry'
            revoked = (
                'did not revoke the refresh token (the CLI cannot read the '
                'entry)'
            )
        else:
            label = _label(entry)
            reason = _not_revocable(entry)
            if reason is None:
                failure = _revoke(entry, ca_bundle)
                if failure is not None:
                    return self._keep_for_retry(path, entry, label, failure)
            revoked = (
                'revoked the refresh token'
                if reason is None
                else f'did not revoke the refresh token ({reason})'
            )
        if not self._remove_entry(path, f'{label}: {revoked}'):
            return False
        write_status(f'{label}: {revoked}; removed the sign-in.')
        return True

    def _keep_for_retry(self, path, entry, label, failure):
        """Keep the refresh token that failed to revoke, then delete the entry.

        Returns False: the refresh token is still valid. If the token cannot
        be kept, the entry stays, so the revocation can still be retried.
        """
        try:
            cache.add_pending_revocation(entry)
        except (OSError, AgentRegistryJWTError) as e:
            write_status(
                f'{label}: could not revoke the refresh token ({failure}), '
                f'and could not keep it to retry the revocation later '
                f'({printable(e)}). Left the sign-in in place so the '
                f'revocation can be retried: {_retry_advice(entry)}.'
            )
            return False
        if self._remove_entry(
            path,
            f'{label}: could not revoke the refresh token ({failure}); kept '
            f'it so the revocation can be retried',
        ):
            write_status(
                f'{label}: could not revoke the refresh token ({failure}). '
                f'Removed the sign-in from this machine and kept the refresh '
                f'token so the revocation can be retried: '
                f'{_retry_advice(entry)}.'
            )
        return False

    def _remove_entry(self, path, outcome):
        """Delete an entry file; report ``outcome`` if that fails."""
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        except OSError as e:
            write_status(f'{outcome}; could not remove {path}: {printable(e)}')
            return False
        return True
