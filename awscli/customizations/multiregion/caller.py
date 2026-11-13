# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import copy
import logging
import socket

from botocore.exceptions import (
    ClientError,
    EndpointConnectionError,
    NoCredentialsError,
    NoRegionError,
    ParamValidationError,
    ProfileNotFound,
)
from botocore.utils import ensure_boolean

from awscli.compat import get_stderr_text_writer
from awscli.customizations.exceptions import (
    ParamValidationError as CLIParamValidationError,
)
from awscli.customizations.multiregion.merge import (
    annotate_response,
    merge_responses,
)
from awscli.customizations.multiregion.pagination import (
    count_items,
    decode_token,
    encode_token,
    get_input_tokens,
    get_response_tokens,
    pop_pagination_tokens,
    region_parameters,
    with_next_token,
)
from awscli.customizations.multiregion.resolution import resolve_regions
from awscli.customizations.multiregion.validation import (
    validate_call_parameters,
)

LOG = logging.getLogger(__name__)

_STREAMED_OUTPUT_FORMATS = ('yaml-stream', 'text')
_NO_ENDPOINT_MESSAGE = 'could not resolve any endpoint; check network or DNS'

# Failures that are the same in every region, so they are reported once.
_REGION_INDEPENDENT_ERRORS = (
    NoCredentialsError,
    NoRegionError,
    ParamValidationError,
    ProfileNotFound,
)


class MultiRegionOperationCaller:
    """Call an operation in several regions, one after another.

    A caller runs one command, so it also holds that run's results.
    """

    def __init__(self, session, operation_caller, spec, offline=False):
        self._session = session
        self._operation_caller = operation_caller
        self._spec = spec
        self._offline = offline
        # Regions whose results stopped early and cannot be resumed.
        self._truncated = []
        # The token that resumes the listing, once known.
        self._next_token = []

    def invoke(self, service_name, operation_name, parameters, parsed_globals):
        """Run ``operation_name`` in every region of the spec."""

        operation_model = self._session.get_service_model(
            service_name
        ).operation_model(operation_name)
        validate_call_parameters(
            parameters,
            get_input_tokens(self._session, service_name, operation_model),
        )
        if parsed_globals.sign_request and not self._offline:
            self._resolve_credentials()
        # Before resolving the regions: ``all`` makes API calls too.  A
        # skeleton sends no request, so like credentials it is not checked.
        if not self._offline:
            self._reject_configured_endpoint_url(service_name)
        resolved = resolve_regions(
            self._session,
            self._spec,
            service_name,
            verify=parsed_globals.verify_ssl,
            offline=self._offline,
        )
        responses = self._iter_responses(
            resolved, service_name, operation_model, parameters, parsed_globals
        )
        output = parsed_globals.output or self._session.get_config_variable(
            'output'
        )
        # A --query must see every region at once: applied to each region
        # on its own, length(), sort_by(), [0] and the like give per-region
        # answers instead of one answer for the whole command.
        if output in _STREAMED_OUTPUT_FORMATS and parsed_globals.query is None:
            # Print each region as it finishes, like pages of one region.
            self._operation_caller._display_response(
                operation_name,
                with_next_token(responses, self._next_token, output),
                parsed_globals,
            )
        else:
            merged = merge_responses(responses)
            if self._next_token:
                merged['NextToken'] = self._next_token[0]
            # A --query is applied even to an empty response, like it is
            # for a single region (which prints null, for example).
            if merged or parsed_globals.query is not None:
                self._operation_caller._display_response(
                    operation_name, merged, parsed_globals
                )
        self._warn_about_truncation()
        return 0

    def _resolve_credentials(self):
        # Resolved once, so a failure is reported once, not per region.
        credentials = self._session.get_credentials()
        if credentials is not None:
            credentials.get_frozen_credentials()

    def _reject_configured_endpoint_url(self, service_name):
        """Reject an endpoint URL set in the environment or config file.

        Every region would be sent to that one endpoint.
        """
        config_store = copy.copy(self._session.get_component('config_store'))
        if ensure_boolean(
            config_store.get_config_variable('ignore_configured_endpoint_urls')
        ):
            return
        self._session._add_configured_endpoint_provider(
            service_name, config_store
        )
        configured = config_store.get_config_variable('endpoint_url')
        if configured is None:
            return
        raise CLIParamValidationError(
            'A configured endpoint URL cannot be used together with '
            f'--multi-regions: every region would be sent to {configured}. '
            'Unset AWS_ENDPOINT_URL, AWS_ENDPOINT_URL_<SERVICE> or the '
            'endpoint_url config setting to run across regions.'
        )

    def _iter_responses(
        self,
        resolved,
        service_name,
        operation_model,
        parameters,
        parsed_globals,
    ):
        response_tokens = get_response_tokens(
            self._session, service_name, operation_model
        )
        pagination_config = parameters.get('PaginationConfig', {})
        start_index, region_token = 0, None
        if pagination_config.get('StartingToken'):
            start_index, region_token = decode_token(
                pagination_config['StartingToken'], resolved.regions
            )
        # Regions left out because their hostname does not exist.
        skipped = []
        last_dns_error = None
        # --max-items limits the whole command, not each region.
        remaining = pagination_config.get('MaxItems')
        if remaining is not None:
            # A string when the paginator's limit key is a string
            remaining = int(remaining)
        regions = resolved.regions[start_index:]
        for region in regions:
            if remaining is not None and remaining <= 0:
                self._next_token.append(encode_token(region, None))
                return
            page_iterator = None
            try:
                client = self._session.create_client(
                    service_name,
                    region_name=region,
                    verify=parsed_globals.verify_ssl,
                )
                response = self._operation_caller._make_client_call(
                    client,
                    operation_model.name,
                    region_parameters(parameters, remaining, region_token),
                    parsed_globals,
                )
                region_token = None
                if hasattr(response, 'build_full_result'):
                    page_iterator = response
                    response = page_iterator.build_full_result()
                    if remaining is not None:
                        remaining -= count_items(page_iterator, response)
            except _REGION_INDEPENDENT_ERRORS:
                # Reported once by the CLI's error handlers.
                raise
            except Exception as e:
                if resolved.skip_missing_hosts and _is_dns_failure(e):
                    # The service does not exist in this region.
                    LOG.debug(
                        'Skipping %s: no endpoint for %s in that region (%s)',
                        region,
                        service_name,
                        e,
                    )
                    skipped.append(region)
                    last_dns_error = e
                    continue
                LOG.debug(
                    'Error calling %s in %s',
                    operation_model.name,
                    region,
                    exc_info=True,
                )
                # Any other failure stops the command.
                raise _add_context(e, f'[{region}]')
            response.pop('ResponseMetadata', None)
            # Only a paginated listing can be resumed (see below).
            if (
                pop_pagination_tokens(response, response_tokens)
                and page_iterator is None
            ):
                if not self._offline:
                    self._truncated.append(region)
                elif not self._next_token:
                    # A skeleton shows where the token goes.
                    self._next_token.append('NextToken')
            yield annotate_response(response, region)
            if page_iterator is not None and page_iterator.resume_token:
                self._next_token.append(
                    encode_token(region, page_iterator.resume_token)
                )
                return
        resumed = bool(pagination_config.get('StartingToken'))
        if skipped and len(skipped) == len(regions) and not resumed:
            # No hostname resolved anywhere: a network or DNS problem.  A
            # resumed listing already reached an endpoint, so the regions
            # left only lack the service.
            raise _add_context(
                last_dns_error,
                f'[{", ".join(skipped)}] {_NO_ENDPOINT_MESSAGE}:',
            )

    def _warn_about_truncation(self):
        if not self._truncated:
            return
        stderr = get_stderr_text_writer()
        for region in self._truncated:
            stderr.write(
                f'[{region}] the results are incomplete: this region '
                'returned a pagination token, which cannot be used with '
                '--multi-regions. Re-run the command for this region on '
                'its own to page through the rest.\n'
            )
        stderr.flush()


def _add_context(error, context):
    """Put ``context`` in front of the message of ``error``."""
    error.args = (f'{context} {error}',) + error.args[1:]
    if isinstance(error, ClientError):
        details = error.response.get('Error', {})
        details['Message'] = f"{context} {details.get('Message', '')}".strip()
    return error


def _is_dns_failure(exception):
    """Report whether the endpoint hostname does not exist."""
    if not isinstance(exception, EndpointConnectionError):
        return False
    cause = exception.kwargs.get('error')
    while cause is not None:
        if isinstance(cause, socket.gaierror):
            return cause.errno in _NO_SUCH_HOST_ERRNOS
        cause = cause.__cause__ or cause.__context__
    return False


# EAI_NODATA is not defined on every platform.
_NO_SUCH_HOST_ERRNOS = frozenset(
    errno
    for errno in (
        getattr(socket, 'EAI_NONAME', None),
        getattr(socket, 'EAI_NODATA', None),
    )
    if errno is not None
)
