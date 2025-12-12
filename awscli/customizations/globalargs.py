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
import sys
import os

from awscli.customizations.argrename import HIDDEN_ALIASES
from awscli.customizations.utils import uni_print
from botocore.client import Config
from botocore import UNSIGNED
from botocore.endpoint import DEFAULT_TIMEOUT
from botocore.useragent import register_feature_id
import jmespath

from awscli.compat import urlparse
from awscli.utils import resolve_v2_debug_mode


def register_parse_global_args(cli):
    cli.register('top-level-args-parsed', resolve_types,
                 unique_id='resolve-types')
    cli.register('top-level-args-parsed', no_sign_request,
                 unique_id='no-sign')
    cli.register('top-level-args-parsed', resolve_verify_ssl,
                 unique_id='resolve-verify-ssl')
    cli.register('top-level-args-parsed', resolve_cli_read_timeout,
                 unique_id='resolve-cli-read-timeout')
    cli.register('top-level-args-parsed', resolve_cli_connect_timeout,
                 unique_id='resolve-cli-connect-timeout')
    cli.register('top-level-args-parsed', detect_migration_breakage,
                 unique_id='detect-migration-breakage')


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
        raise ValueError("Bad value for --query %s: %s" % (value, str(e)))


def _resolve_endpoint_url(value):
    parsed = urlparse.urlparse(value)
    # Our http library requires you specify an endpoint url
    # that contains a scheme, so we'll verify that up front.
    if not parsed.scheme:
        raise ValueError('Bad value for --endpoint-url "%s": scheme is '
                         'missing.  Must be of the form '
                         'http://<hostname>/ or https://<hostname>/' % value)
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

def detect_migration_breakage(parsed_args, session, remaining_args, **kwargs):
    if not resolve_v2_debug_mode(parsed_args):
        return
    region = parsed_args.region or session.get_config_variable('region')
    s3_config = session.get_config_variable('s3')
    if (
            not session.get_scoped_config().get('cli_pager', None)
            == '' and 'AWS_PAGER' not in os.environ
    ):
        uni_print(
            '\nAWS CLI v2 UPGRADE WARNING: By default, the AWS CLI v2 returns '
            'all output through your operating system’s default pager '
            'program. This is different from v1 behavior, where the system '
            'pager is not used by default. To retain AWS CLI v1 behavior in '
            'AWS CLI v2, set the `cli_pager` configuration setting, or the '
            '`AWS_PAGER` environment variable, to the empty string. See '
            'https://docs.aws.amazon.com/cli/latest/userguide/'
            'cliv2-migration-changes.html#cliv2-migration-output-pager.\n',
            out_file=sys.stderr
        )
    if 'PYTHONUTF8' in os.environ or 'PYTHONIOENCODING' in os.environ:
        if 'AWS_CLI_FILE_ENCODING' not in os.environ:
            uni_print(
                '\nThe AWS CLI v2 does not support The `PYTHONUTF8` and '
                '`PYTHONIOENCODING` environment variables, and instead uses '
                'the `AWS_CLI_FILE_ENCODING` variable. This is different from '
                'v1 behavior, where the former two variables are used '
                'instead. To retain AWS CLI v1 behavior in AWS CLI v2, set '
                'the `AWS_CLI_FILE_ENCODING` environment variable instead. '
                'See https://docs.aws.amazon.com/cli/latest/userguide/'
                'cliv2-migration-changes.html'
                '#cliv2-migration-encodingenvvar.\n',
                out_file=sys.stderr
            )
    if (
            (
                s3_config is None
                or s3_config.get('us_east_1_regional_endpoint', 'legacy')
                == 'legacy'
            )
            and region in ('us-east-1', None)
    ):
        session.register(
            'request-created.s3.*',
            warn_if_east_configured_global_endpoint
        )
        session.register(
            'request-created.s3api.*',
            warn_if_east_configured_global_endpoint
        )
    if session.get_config_variable('api_versions'):
        uni_print(
            '\nAWS CLI v2 UPGRADE WARNING: AWS CLI v2 UPGRADE WARNING: '
            'The AWS CLI v2 does not support calling older versions of AWS '
            'service APIs via the `api_versions` configuration file setting. This '
            'is different from v1 behavior, where this configuration setting '
            'can be used to pin older API versions. To migrate to v2 '
            'behavior, remove the `api_versions` configuration setting, and '
            'test against the latest service API versions. See '
            'https://docs.aws.amazon.com/cli/latest/userguide/'
            'cliv2-migration-changes.html#cliv2-migration-api-versions.\n',
            out_file = sys.stderr
        )
    if session.full_config.get('plugins', {}):
        uni_print(
            '\nAWS CLI v2 UPGRADE WARNING: In AWS CLI v2, plugins are '
            'disabled by default, and support for plugins is provisional. '
            'This is different from v1 behavior, where plugin support is URL '
            'below to update your configuration to enable plugins in AWS CLI '
            'v2. Also, be sure to lock into a particular version of the AWS '
            'CLI and test the functionality of your plugins every time AWS '
            'CLI v2 is upgraded. See https://docs.aws.amazon.com/cli/latest/'
            'userguide/cliv2-migration-changes.html'
            '#cliv2-migration-profile-plugins.\n',
            out_file=sys.stderr
        )
    if (
            parsed_args.command == 'ecr' and
            remaining_args is not None and
            remaining_args[0] == 'get-login'
    ):
        uni_print(
            '\nAWS CLI v2 UPGRADE WARNING: The `ecr get-login` command has '
            'been removed in AWS CLI v2. You must use `ecr get-login-password` '
            'instead. See https://docs.aws.amazon.com/cli/latest/userguide/'
            'cliv2-migration-changes.html#cliv2-migration-ecr-get-login.\n',
            out_file=sys.stderr
        )
    for working, obsolete in HIDDEN_ALIASES.items():
        working_split = working.split('.')
        working_service = working_split[0]
        working_cmd = working_split[1]
        working_param = working_split[2]
        if (
                parsed_args.command == working_service
                and remaining_args is not None
                and remaining_args[0] == working_cmd
                and f"--{working_param}" in remaining_args
        ):
            uni_print(
                '\nAWS CLI v2 UPGRADE WARNING: You have entered command '
                'arguments that use at least 1 of 21 built-in ("hidden") '
                'aliases that were removed in AWS CLI v2. For this command '
                'to work in AWS CLI v2, you must replace usage of the alias '
                'with the corresponding parameter in AWS CLI v2. See '
                'https://docs.aws.amazon.com/cli/latest/userguide/'
                'cliv2-migration-changes.html#cliv2-migration-aliases.\n',
                out_file=sys.stderr
            )
    # Register against the provide-client-params event to ensure that the
    # feature ID is registered before any API requests are made. We
    # cannot register the feature ID in this function because no
    # botocore context is created at this point.
    session.register(
        'provide-client-params.*.*',
        _register_v2_debug_feature_id
    )
    session.register('choose-signer.s3.*', warn_if_sigv2)


def _register_v2_debug_feature_id(params, model, **kwargs):
    register_feature_id('CLI_V1_TO_V2_MIGRATION_DEBUG_MODE')

def warn_if_east_configured_global_endpoint(request, operation_name, **kwargs):
    # The regional us-east-1 endpoint is used in certain cases (e.g.
    # FIPS/Dual-Stack is enabled). Rather than duplicating this logic
    # from botocore, we check the endpoint URL directly.
    parsed_url = urlparse.urlparse(request.url)
    if parsed_url.hostname.endswith('s3.amazonaws.com'):
        uni_print(
            '\nAWS CLI v2 UPGRADE WARNING: When you configure AWS CLI v2 to '
            'use the `us-east-1` region, it uses the true regional endpoint '
            'rather than the global endpoint. This is different from v1 '
            'behavior, where the global endpoint would be used when the '
            'region is `us-east-1`. To retain AWS CLI v1 behavior in AWS '
            'CLI v2, configure the region setting to `aws-global`. See '
            'https://docs.aws.amazon.com/cli/latest/userguide/'
            'cliv2-migration-changes.html'
            '#cliv2-migration-s3-regional-endpoint.\n',
            out_file=sys.stderr
        )

def warn_if_sigv2(
        signing_name,
        region_name,
        signature_version,
        context,
        **kwargs
):
    if context.get('auth_type', None) == 'v2':
        uni_print(
            '\nAWS CLI v2 UPGRADE WARNING: The AWS CLI v2 only uses Signature '
            'v4 to authenticate Amazon S3 requests. This is different from '
            'v1 behavior, where the signature used for Amazon S3 requests may '
            'vary depending on configuration settings, region, and the '
            'bucket being used. To migrate to AWS CLI v2 behavior, configure '
            'the Signature Version S3 setting to version 4. See '
            'https://docs.aws.amazon.com/cli/latest/userguide/'
            'cliv2-migration-changes.html#cliv2-migration-sigv4.\n',
            out_file=sys.stderr
        )

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
