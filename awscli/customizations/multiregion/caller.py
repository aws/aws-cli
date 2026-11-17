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
    empty_response,
    merge_responses,
)
from awscli.customizations.multiregion.pagination import (
    count_items,
    decode_token,
    encode_token,
    get_pagination_tokens,
    pop_pagination_tokens,
    region_parameters,
)
from awscli.customizations.multiregion.resolution import resolve_regions
from awscli.customizations.multiregion.validation import (
    validate_call_parameters,
)

LOG = logging.getLogger(__name__)

_STREAMED_OUTPUT_FORMATS = ('yaml-stream', 'text')
_NO_ENDPOINT_MESSAGE = 'could not resolve any endpoint; check network or DNS'
_NO_VARIANT_ENDPOINT_MESSAGE = (
    'could not resolve any endpoint; the service may have no FIPS or '
    'dual-stack endpoint in these regions, or check network or DNS'
)

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

    def __init__(self, session, operation_caller, spec):
        self._session = session
        self._operation_caller = operation_caller
        self._spec = spec
        # Regions whose results stopped early and cannot be resumed.
        self._truncated = []
        # Regions left out because their hostname does not exist.
        self._skipped = []
        # The token that resumes the listing, once known.
        self._next_token = None

    def invoke(self, service_name, operation_name, parameters, parsed_globals):
        """Run ``operation_name`` in every region of the spec."""

        operation_model = self._session.get_service_model(
            service_name
        ).operation_model(operation_name)
        input_tokens, response_tokens = get_pagination_tokens(
            self._session, service_name, operation_model
        )
        validate_call_parameters(parameters, input_tokens)
        if parsed_globals.sign_request:
            self._resolve_credentials()
        # Before resolving the regions: ``all`` makes API calls too.
        self._reject_configured_endpoint_url(service_name)
        resolved = resolve_regions(
            self._session,
            self._spec,
            service_name,
            verify=parsed_globals.verify_ssl,
        )
        responses = self._iter_responses(
            resolved,
            service_name,
            operation_model,
            response_tokens,
            parameters,
            parsed_globals,
        )
        # Printed like a region with nothing to list when no region
        # answers, e.g. when a resumed listing only has regions left out.
        empty = empty_response(operation_model, response_tokens)
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
                self._stream(responses, empty, output),
                parsed_globals,
            )
        else:
            responses = list(responses)
            merged = merge_responses(responses) if responses else empty
            if self._next_token is not None:
                merged['NextToken'] = self._next_token
            # A --query is applied even to an empty response, like it is
            # for a single region (which prints null, for example).
            if merged or parsed_globals.query is not None:
                self._operation_caller._display_response(
                    operation_name, merged, parsed_globals
                )
        if resolved.endpoint_variant:
            self._warn_about_skipped_regions(service_name)
        self._warn_about_truncation()
        return 0

    def _stream(self, responses, empty, output):
        """The regions that have something to list, then the token.

        A region with nothing to list is left out, since it would print
        nothing that names its region.
        """
        printed = False
        for response in responses:
            if any(response.values()):
                printed = True
                yield response
        if not printed:
            yield empty
        # Like the pages of one region: only text prints the token.
        if self._next_token is not None and output == 'text':
            yield {'NextToken': {'NextToken': self._next_token}}

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
        response_tokens,
        parameters,
        parsed_globals,
    ):
        pagination_config = parameters.get('PaginationConfig', {})
        starting_token = pagination_config.get('StartingToken')
        start_index, region_token = 0, None
        if starting_token:
            start_index, region_token = decode_token(
                starting_token, resolved.regions
            )
        last_dns_error = None
        # --max-items limits the whole command, not each region.
        remaining = pagination_config.get('MaxItems')
        if remaining is not None:
            # A string when the paginator's limit key is a string
            remaining = int(remaining)
        regions = resolved.regions[start_index:]
        for region in regions:
            if remaining is not None and remaining <= 0:
                self._next_token = encode_token(region, None)
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
                    # The service, or its endpoint variant, does not exist
                    # in this region.
                    LOG.debug(
                        'Skipping %s: no endpoint for %s in that region (%s)',
                        region,
                        service_name,
                        e,
                    )
                    self._skipped.append(region)
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
                self._truncated.append(region)
            yield annotate_response(response, region)
            if page_iterator is not None and page_iterator.resume_token:
                self._next_token = encode_token(
                    region, page_iterator.resume_token
                )
                return
        if (
            self._skipped
            and len(self._skipped) == len(regions)
            and not starting_token
        ):
            # No hostname resolved anywhere: a network or DNS problem, or
            # no region has the endpoint variant.  A resumed listing
            # already reached an endpoint, so the regions left only lack
            # the service or its endpoint variant.
            message = (
                _NO_VARIANT_ENDPOINT_MESSAGE
                if resolved.endpoint_variant
                else _NO_ENDPOINT_MESSAGE
            )
            raise _add_context(
                last_dns_error,
                f'[{", ".join(self._skipped)}] {message}:',
            )

    def _warn_about_skipped_regions(self, service_name):
        # Without an endpoint variant, a region is only left out when the
        # service was never launched there, which is not worth a notice.
        if not self._skipped:
            return
        stderr = get_stderr_text_writer()
        stderr.write(
            f'[{", ".join(self._skipped)}] skipped: no FIPS or dual-stack '
            f'endpoint for {service_name} there, so the results leave '
            'these regions out.\n'
        )
        stderr.flush()

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
