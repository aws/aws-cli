# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
import sys

import jmespath
from botocore import UNSIGNED
from botocore.client import Config
from botocore.endpoint import DEFAULT_TIMEOUT

from awscli.compat import urlparse
from awscli.customizations.exceptions import ParamValidationError


def register_parse_global_args(cli):
    cli.register(
        'top-level-args-parsed', resolve_types, unique_id='resolve-types'
    )
    cli.register('top-level-args-parsed', no_sign_request, unique_id='no-sign')
    cli.register(
        'top-level-args-parsed',
        resolve_verify_ssl,
        unique_id='resolve-verify-ssl',
    )
    cli.register(
        'top-level-args-parsed',
        resolve_cli_read_timeout,
        unique_id='resolve-cli-read-timeout',
    )
    cli.register(
        'top-level-args-parsed',
        resolve_cli_connect_timeout,
        unique_id='resolve-cli-connect-timeout',
    )
    cli.register(
        'session-initialized',
        resolve_apn_id,
        unique_id='resolve-apn-id',
    )


def resolve_types(parsed_args, **kwargs):
    # This emulates the "type" arg from argparse, but does so in a way
    # that plugins can also hook into this process.
    _resolve_arg(parsed_args, 'query')
    _resolve_arg(parsed_args, 'endpoint_url')


def _resolve_arg(parsed_args, name):
    value = getattr(parsed_args, name, None)
    if value is not None:
        new_value = getattr(sys.modules[__name__], '_resolve_%s' % name)(value)
        setattr(parsed_args, name, new_value)


def _resolve_query(value):
    try:
        return jmespath.compile(value)
    except Exception as e:
        raise ParamValidationError(
            "Bad value for --query %s: %s" % (value, str(e))
        )


def _resolve_endpoint_url(value):
    parsed = urlparse.urlparse(value)
    # Our http library requires you specify an endpoint url
    # that contains a scheme, so we'll verify that up front.
    if not parsed.scheme:
        raise ParamValidationError(
            'Bad value for --endpoint-url "%s": scheme is '
            'missing.  Must be of the form '
            'http://<hostname>/ or https://<hostname>/' % value
        )
    return value


def resolve_verify_ssl(parsed_args, session, **kwargs):
    arg_name = 'verify_ssl'
    arg_value = getattr(parsed_args, arg_name, None)
    if arg_value is not None:
        verify = None
        # Only consider setting a custom ca_bundle if they
        # haven't provided --no-verify-ssl.
        if not arg_value:
            verify = False
        else:
            # in case if `ca_bundle` not in args it'll be retrieved
            # from config on session.client creation step
            verify = getattr(parsed_args, 'ca_bundle', None)
        setattr(parsed_args, arg_name, verify)


def no_sign_request(parsed_args, session, **kwargs):
    if not parsed_args.sign_request:
        # Disable request signing by setting the signature version to UNSIGNED
        # in the default client configuration. This ensures all new clients
        # will be created with signing disabled.
        _update_default_client_config(session, 'signature_version', UNSIGNED)


def resolve_cli_connect_timeout(parsed_args, session, **kwargs):
    arg_name = 'connect_timeout'
    _resolve_timeout(session, parsed_args, arg_name)


def resolve_cli_read_timeout(parsed_args, session, **kwargs):
    arg_name = 'read_timeout'
    _resolve_timeout(session, parsed_args, arg_name)


def _resolve_timeout(session, parsed_args, arg_name):
    arg_value = getattr(parsed_args, arg_name, None)
    if arg_value is None:
        arg_value = DEFAULT_TIMEOUT
    arg_value = int(arg_value)
    if arg_value == 0:
        arg_value = None
    setattr(parsed_args, arg_name, arg_value)
    # Update in the default client config so that the timeout will be used
    # by all clients created from then on.
    _update_default_client_config(session, arg_name, arg_value)


def _update_default_client_config(session, arg_name, arg_value):
    current_default_config = session.get_default_client_config()
    new_default_config = Config(**{arg_name: arg_value})
    if current_default_config is not None:
        new_default_config = current_default_config.merge(new_default_config)
    session.set_default_client_config(new_default_config)


# Allowed characters for APN ID values: ASCII letters, digits,
# underscore, and hyphen.  Simple set check avoids regex entirely.
_APN_ID_ALLOWED_CHARS = frozenset(
    'abcdefghijklmnopqrstuvwxyz' 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' '0123456789' '_-'
)


def _is_valid_apn_id(value):
    """Validate an APN ID value: 1-255 chars from the allowed set."""
    if not value or len(value) > 255:
        return False
    return all(c in _APN_ID_ALLOWED_CHARS for c in value)


def resolve_apn_id(parsed_args, session, **kwargs):
    """Resolve the APN ID from CLI flag, env var, or config file.

    Registered on 'session-initialized' so the profile is already set
    and config file values are accessible.
    """
    apn_id = getattr(parsed_args, 'apn_id', None)
    if apn_id is None:
        apn_id = os.environ.get('AWS_APN_ID')
    if apn_id is None:
        try:
            scoped_config = session.get_scoped_config()
            apn_id = scoped_config.get('apn_id')
        except Exception:
            pass
    if not apn_id:
        return
    if not _is_valid_apn_id(apn_id):
        raise ParamValidationError(
            "Bad value for --apn-id %r: must be 1-255 characters and may "
            "only contain letters, digits, '_', and '-'." % apn_id
        )
    # Format defined by the AWS PRM onboarding guide:
    # https://docs.aws.amazon.com/PRM/latest/aws-prm-onboarding-guide/user-agent-string.html
    # The trailing '$' is a required end delimiter, not a regex anchor.
    # The user provides the full identifier including the type prefix
    # (e.g. "pc_PRODUCTCODE" or "ra_ATTRIBUTIONID").
    marker = 'APN_1.1/%s$' % apn_id
    existing = session.user_agent_extra or ''
    if marker in existing.split():
        return
    session.user_agent_extra = (
        '%s %s' % (existing, marker) if existing else marker
    )
