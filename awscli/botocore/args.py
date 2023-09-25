# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
"""Internal module to help with normalizing botocore client args.

This module (and all function/classes within this module) should be
considered internal, and *not* a public API.

"""
import copy
import logging
import socket

import botocore.exceptions
import botocore.serialize
from botocore.config import Config
from botocore.endpoint import EndpointCreator
from botocore.regions import EndpointResolverBuiltins as EPRBuiltins
from botocore.regions import EndpointRulesetResolver
from botocore.signers import RequestSigner
from botocore.utils import ensure_boolean, is_s3_accelerate_url

logger = logging.getLogger(__name__)


class ClientArgsCreator(object):
    def __init__(self, event_emitter, user_agent, response_parser_factory,
                 loader, exceptions_factory, config_store):
        self._event_emitter = event_emitter
        self._user_agent = user_agent
        self._response_parser_factory = response_parser_factory
        self._loader = loader
        self._exceptions_factory = exceptions_factory
        self._config_store = config_store

    def get_client_args(
            self,
            service_model,
            region_name,
            is_secure,
            endpoint_url,
            verify,
            credentials,
            scoped_config,
            client_config,
            endpoint_bridge,
            auth_token=None,
            endpoints_ruleset_data=None,
            partition_data=None,
    ):
        final_args = self.compute_client_args(
            service_model, client_config, endpoint_bridge, region_name,
            endpoint_url, is_secure, scoped_config)

        service_name = final_args['service_name']
        parameter_validation = final_args['parameter_validation']
        endpoint_config = final_args['endpoint_config']
        protocol = final_args['protocol']
        config_kwargs = final_args['config_kwargs']
        s3_config = final_args['s3_config']
        partition = endpoint_config['metadata'].get('partition', None)
        socket_options = final_args['socket_options']
        configured_endpoint_url = final_args['configured_endpoint_url']
        signing_region = endpoint_config['signing_region']
        endpoint_region_name = endpoint_config['region_name']

        event_emitter = copy.copy(self._event_emitter)
        signer = RequestSigner(
            service_model.service_id, signing_region,
            endpoint_config['signing_name'],
            endpoint_config['signature_version'],
            credentials, event_emitter, auth_token
        )

        config_kwargs['s3'] = s3_config
        new_config = Config(**config_kwargs)
        endpoint_creator = EndpointCreator(event_emitter)

        endpoint = endpoint_creator.create_endpoint(
            service_model, region_name=endpoint_region_name,
            endpoint_url=endpoint_config['endpoint_url'], verify=verify,
            response_parser_factory=self._response_parser_factory,
            max_pool_connections=new_config.max_pool_connections,
            proxies=new_config.proxies,
            timeout=(new_config.connect_timeout, new_config.read_timeout),
            socket_options=socket_options,
            client_cert=new_config.client_cert,
            proxies_config=new_config.proxies_config)

        serializer = botocore.serialize.create_serializer(
            protocol, parameter_validation)
        response_parser = botocore.parsers.create_parser(protocol)

        ruleset_resolver = self._build_endpoint_resolver(
            endpoints_ruleset_data,
            partition_data,
            client_config,
            service_model,
            endpoint_region_name,
            region_name,
            configured_endpoint_url,
            endpoint,
            is_secure,
            endpoint_bridge,
            event_emitter,
        )

        return {
            'serializer': serializer,
            'endpoint': endpoint,
            'response_parser': response_parser,
            'event_emitter': event_emitter,
            'request_signer': signer,
            'service_model': service_model,
            'loader': self._loader,
            'client_config': new_config,
            'partition': partition,
            'exceptions_factory': self._exceptions_factory,
            'endpoint_ruleset_resolver': ruleset_resolver,
        }

    def compute_client_args(self, service_model, client_config,
                            endpoint_bridge, region_name, endpoint_url,
                            is_secure, scoped_config):
        service_name = service_model.endpoint_prefix
        protocol = service_model.metadata['protocol']
        parameter_validation = True
        if client_config and not client_config.parameter_validation:
            parameter_validation = False
        elif scoped_config:
            raw_value = scoped_config.get('parameter_validation')
            if raw_value is not None:
                parameter_validation = ensure_boolean(raw_value)

        # Override the user agent if specified in the client config.
        user_agent = self._user_agent
        if client_config is not None:
            if client_config.user_agent is not None:
                user_agent = client_config.user_agent
            if client_config.user_agent_extra is not None:
                user_agent += ' %s' % client_config.user_agent_extra

        s3_config = self.compute_s3_config(client_config)

        configured_endpoint_url = self._compute_configured_endpoint_url(
            client_config=client_config,
            endpoint_url=endpoint_url,
        )

        endpoint_config = self._compute_endpoint_config(
            service_name=service_name,
            region_name=region_name,
            endpoint_url=configured_endpoint_url,
            is_secure=is_secure,
            endpoint_bridge=endpoint_bridge,
            s3_config=s3_config,
        )
        endpoint_variant_tags = endpoint_config['metadata'].get('tags', [])
        # Create a new client config to be passed to the client based
        # on the final values. We do not want the user to be able
        # to try to modify an existing client with a client config.
        config_kwargs = dict(
            region_name=endpoint_config['region_name'],
            signature_version=endpoint_config['signature_version'],
            user_agent=user_agent)
        if 'dualstack' in endpoint_variant_tags:
            config_kwargs.update(use_dualstack_endpoint=True)
        if 'fips' in endpoint_variant_tags:
            config_kwargs.update(use_fips_endpoint=True)
        if client_config is not None:
            config_kwargs.update(
                connect_timeout=client_config.connect_timeout,
                read_timeout=client_config.read_timeout,
                max_pool_connections=client_config.max_pool_connections,
                proxies=client_config.proxies,
                proxies_config=client_config.proxies_config,
                retries=client_config.retries,
                client_cert=client_config.client_cert,
                inject_host_prefix=client_config.inject_host_prefix,
                request_min_compression_size_bytes=(
                    client_config.request_min_compression_size_bytes
                ),
                disable_request_compression=(
                    client_config.disable_request_compression
                ),
            )
        self._compute_retry_config(config_kwargs)
        self._compute_request_compression_config(config_kwargs)
        s3_config = self.compute_s3_config(client_config)

        is_s3_service = self._is_s3_service(service_name)

        if is_s3_service and 'dualstack' in endpoint_variant_tags:
            if s3_config is None:
                s3_config = {}
            s3_config['use_dualstack_endpoint'] = True

        return {
            'service_name': service_name,
            'parameter_validation': parameter_validation,
            'user_agent': user_agent,
            'configured_endpoint_url': configured_endpoint_url,
            'endpoint_config': endpoint_config,
            'protocol': protocol,
            'config_kwargs': config_kwargs,
            's3_config': s3_config,
            'socket_options': self._compute_socket_options(scoped_config)
        }

    def _compute_configured_endpoint_url(self, client_config, endpoint_url):
        if endpoint_url is not None:
            return endpoint_url

        if self._ignore_configured_endpoint_urls(client_config):
            logger.debug("Ignoring configured endpoint URLs.")
            return endpoint_url

        return self._config_store.get_config_variable('endpoint_url')

    def _ignore_configured_endpoint_urls(self, client_config):
        if (
            client_config
            and client_config.ignore_configured_endpoint_urls is not None
        ):
            return client_config.ignore_configured_endpoint_urls

        return self._config_store.get_config_variable(
            'ignore_configured_endpoint_urls'
        )

    def compute_s3_config(self, client_config):
        s3_configuration = self._config_store.get_config_variable('s3')

        # Next specific client config values takes precedence over
        # specific values in the scoped config.
        if client_config is not None:
            if client_config.s3 is not None:
                if s3_configuration is None:
                    s3_configuration = client_config.s3
                else:
                    # The current s3_configuration dictionary may be
                    # from a source that only should be read from so
                    # we want to be safe and just make a copy of it to modify
                    # before it actually gets updated.
                    s3_configuration = s3_configuration.copy()
                    s3_configuration.update(client_config.s3)

        return s3_configuration

    def _is_s3_service(self, service_name):
        """Whether the service is S3 or S3 Control.

        Note that throughout this class, service_name refers to the endpoint
        prefix, not the folder name of the service in botocore/data. For
        S3 Control, the folder name is 's3control' but the endpoint prefix is
        's3-control'.
        """
        return service_name in ['s3', 's3-control']

    def _compute_endpoint_config(self, service_name, region_name, endpoint_url,
                                 is_secure, endpoint_bridge, s3_config):
        resolve_endpoint_kwargs = {
            'service_name': service_name,
            'region_name': region_name,
            'endpoint_url': endpoint_url,
            'is_secure': is_secure,
            'endpoint_bridge': endpoint_bridge,
        }
        if service_name == 's3':
            return self._compute_s3_endpoint_config(
                s3_config=s3_config, **resolve_endpoint_kwargs)
        return self._resolve_endpoint(**resolve_endpoint_kwargs)

    def _compute_s3_endpoint_config(self, s3_config,
                                    **resolve_endpoint_kwargs):
        endpoint_config = self._resolve_endpoint(**resolve_endpoint_kwargs)
        self._set_region_if_custom_s3_endpoint(
            endpoint_config, resolve_endpoint_kwargs['endpoint_bridge'])
        return endpoint_config

    def _set_region_if_custom_s3_endpoint(self, endpoint_config,
                                          endpoint_bridge):
        # If a user is providing a custom URL, the endpoint resolver will
        # refuse to infer a signing region. If we want to default to s3v4,
        # we have to account for this.
        if endpoint_config['signing_region'] is None \
                and endpoint_config['region_name'] is None:
            endpoint = endpoint_bridge.resolve('s3')
            endpoint_config['signing_region'] = endpoint['signing_region']
            endpoint_config['region_name'] = endpoint['region_name']

    def _resolve_endpoint(self, service_name, region_name,
                          endpoint_url, is_secure, endpoint_bridge):
        return endpoint_bridge.resolve(
            service_name, region_name, endpoint_url, is_secure)

    def _compute_socket_options(self, scoped_config):
        # This disables Nagle's algorithm and is the default socket options
        # in urllib3.
        socket_options = [(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)]
        if scoped_config:
            # Enables TCP Keepalive if specified in shared config file.
            if self._ensure_boolean(scoped_config.get('tcp_keepalive', False)):
                socket_options.append(
                    (socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1))
        return socket_options

    def _compute_retry_config(self, config_kwargs):
        self._compute_retry_max_attempts(config_kwargs)
        self._compute_retry_mode(config_kwargs)

    def _compute_retry_max_attempts(self, config_kwargs):
        # An explicitly provided max_attempts in the client config
        # overrides everything.
        retries = config_kwargs.get('retries')
        if retries is not None and 'max_attempts' in retries:
            return
        # Otherwise we'll check the config store which checks env vars,
        # config files, etc.  There is no default value for max_attempts
        # so if this returns None and we don't set a default value here.
        max_attempts = self._config_store.get_config_variable('max_attempts')
        if max_attempts is not None:
            if retries is None:
                retries = {}
                config_kwargs['retries'] = retries
            retries['max_attempts'] = max_attempts

    def _compute_retry_mode(self, config_kwargs):
        retries = config_kwargs.get('retries')
        if retries is None:
            retries = {}
            config_kwargs['retries'] = retries
        elif 'mode' in retries:
            # If there's a retry mode explicitly set in the client config
            # that overrides everything.
            return
        retry_mode = self._config_store.get_config_variable('retry_mode')
        if retry_mode is None:
            retry_mode = 'standard'
        retries['mode'] = retry_mode

    def _compute_request_compression_config(self, config_kwargs):
        min_size = config_kwargs.get('request_min_compression_size_bytes')
        disabled = config_kwargs.get('disable_request_compression')
        if min_size is None:
            min_size = self._config_store.get_config_variable(
                'request_min_compression_size_bytes'
            )
        # conversion func is skipped so input validation must be done here
        # regardless if the value is coming from the config store or the
        # config object
        min_size = self._validate_min_compression_size(min_size)
        config_kwargs['request_min_compression_size_bytes'] = min_size

        if disabled is None:
            disabled = self._config_store.get_config_variable(
                'disable_request_compression'
            )
        else:
            # if the user provided a value we must check if it's a boolean
            disabled = ensure_boolean(disabled)
        config_kwargs['disable_request_compression'] = disabled

    def _validate_min_compression_size(self, min_size):
        min_allowed_min_size = 1
        max_allowed_min_size = 1048576
        if min_size is not None:
            error_msg_base = (
                f'Invalid value "{min_size}" for '
                'request_min_compression_size_bytes.'
            )
            try:
                min_size = int(min_size)
            except (ValueError, TypeError):
                msg = (
                    f'{error_msg_base} Value must be an integer. '
                    f'Received {type(min_size)} instead.'
                )
                raise botocore.exceptions.InvalidConfigError(error_msg=msg)
            if not min_allowed_min_size <= min_size <= max_allowed_min_size:
                msg = (
                    f'{error_msg_base} Value must be between '
                    f'{min_allowed_min_size} and {max_allowed_min_size}.'
                )
                raise botocore.exceptions.InvalidConfigError(error_msg=msg)

        return min_size

    def _ensure_boolean(self, val):
        if isinstance(val, bool):
            return val
        else:
            return val.lower() == 'true'

    def _build_endpoint_resolver(
        self,
        endpoints_ruleset_data,
        partition_data,
        client_config,
        service_model,
        endpoint_region_name,
        region_name,
        endpoint_url,
        endpoint,
        is_secure,
        endpoint_bridge,
        event_emitter,
    ):
        if endpoints_ruleset_data is None:
            return None

        # The legacy EndpointResolver is global to the session, but
        # EndpointRulesetResolver is service-specific. Builtins for
        # EndpointRulesetResolver must not be derived from the legacy
        # endpoint resolver's output, including final_args, s3_config,
        # etc.
        s3_config_raw = self.compute_s3_config(client_config) or {}
        service_name_raw = service_model.endpoint_prefix
        # Maintain complex logic for s3 and sts endpoints for backwards
        # compatibility.
        if service_name_raw in ['s3', 'sts'] or region_name is None:
            eprv2_region_name = endpoint_region_name
        else:
            eprv2_region_name = region_name
        resolver_builtins = self.compute_endpoint_resolver_builtin_defaults(
            region_name=eprv2_region_name,
            service_name=service_name_raw,
            s3_config=s3_config_raw,
            endpoint_bridge=endpoint_bridge,
            client_endpoint_url=endpoint_url,
            legacy_endpoint_url=endpoint.host,
        )
        # botocore does not support client context parameters generically
        # for every service. Instead, the s3 config section entries are
        # available as client context parameters. In the future, endpoint
        # rulesets of services other than s3/s3control may require client
        # context parameters.
        client_context = (
            s3_config_raw if self._is_s3_service(service_name_raw) else {}
        )
        sig_version = (
            client_config.signature_version
            if client_config is not None
            else None
        )
        return EndpointRulesetResolver(
            endpoint_ruleset_data=endpoints_ruleset_data,
            partition_data=partition_data,
            service_model=service_model,
            builtins=resolver_builtins,
            client_context=client_context,
            event_emitter=event_emitter,
            use_ssl=is_secure,
            requested_auth_scheme=sig_version,
        )

    def compute_endpoint_resolver_builtin_defaults(
        self,
        region_name,
        service_name,
        s3_config,
        endpoint_bridge,
        client_endpoint_url,
        legacy_endpoint_url,
    ):
        # EndpointRulesetResolver rulesets may accept an "SDK::Endpoint" as
        # input. If the endpoint_url argument of create_client() is set, it
        # always takes priority.
        if client_endpoint_url:
            given_endpoint = client_endpoint_url
        # If an endpoints.json data file other than the one bundled within
        # the botocore/data directory is used, the output of legacy
        # endpoint resolution is provided to EndpointRulesetResolver.
        elif not endpoint_bridge.resolver_uses_builtin_data():
            given_endpoint = legacy_endpoint_url
        else:
            given_endpoint = None

        # The endpoint rulesets differ from legacy botocore behavior in whether
        # forcing path style addressing in incompatible situations raises an
        # exception or silently ignores the config setting. The
        # AWS_S3_FORCE_PATH_STYLE parameter is adjusted both here and for each
        # operation so that the ruleset behavior is backwards compatible.
        if s3_config.get('use_accelerate_endpoint', False):
            force_path_style = False
        elif client_endpoint_url is not None and not is_s3_accelerate_url(
            client_endpoint_url
        ):
            force_path_style = s3_config.get('addressing_style') != 'virtual'
        else:
            force_path_style = s3_config.get('addressing_style') == 'path'

        return {
            EPRBuiltins.AWS_REGION: region_name,
            EPRBuiltins.AWS_USE_FIPS: (
                # SDK_ENDPOINT cannot be combined with AWS_USE_FIPS
                given_endpoint is None
                # use legacy resolver's _resolve_endpoint_variant_config_var()
                # or default to False if it returns None
                and endpoint_bridge._resolve_endpoint_variant_config_var(
                    'use_fips_endpoint'
                )
                or False
            ),
            EPRBuiltins.AWS_USE_DUALSTACK: (
                # SDK_ENDPOINT cannot be combined with AWS_USE_DUALSTACK
                given_endpoint is None
                # use legacy resolver's _resolve_use_dualstack_endpoint() and
                # or default to False if it returns None
                and endpoint_bridge._resolve_use_dualstack_endpoint(
                    service_name
                )
                or False
            ),
            EPRBuiltins.AWS_STS_USE_GLOBAL_ENDPOINT: False,
            EPRBuiltins.AWS_S3_USE_GLOBAL_ENDPOINT: False,
            EPRBuiltins.AWS_S3_ACCELERATE: s3_config.get(
                'use_accelerate_endpoint', False
            ),
            EPRBuiltins.AWS_S3_FORCE_PATH_STYLE: force_path_style,
            EPRBuiltins.AWS_S3_USE_ARN_REGION: s3_config.get(
                'use_arn_region', True
            ),
            EPRBuiltins.AWS_S3CONTROL_USE_ARN_REGION: s3_config.get(
                'use_arn_region', False
            ),
            EPRBuiltins.AWS_S3_DISABLE_MRAP: s3_config.get(
                's3_disable_multiregion_access_points', False
            ),
            EPRBuiltins.SDK_ENDPOINT: given_endpoint,
        }
