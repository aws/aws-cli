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

from botocore.paginate import TokenDecoder, TokenEncoder

from awscli.customizations.exceptions import ParamValidationError
from awscli.customizations.paginate import get_paginator_config

# Where botocore puts the resume token of a paginated listing.
_AGGREGATED_RESUME_TOKEN = 'NextToken'


def encode_token(region, region_token):
    """Token that resumes in ``region``, at ``region_token`` if given."""
    return TokenEncoder().encode({'region': region, 'token': region_token})


def decode_token(token, regions):
    """The index of the region to resume in, and that region's token."""
    try:
        decoded = TokenDecoder().decode(token)
        region, region_token = decoded['region'], decoded['token']
    except Exception:
        raise ParamValidationError(
            '--starting-token is not a token returned by a command run '
            'with --multi-regions.'
        )
    if region not in regions:
        raise ParamValidationError(
            f'--starting-token resumes in {region}, which is not one of '
            'the regions of --multi-regions.'
        )
    return regions.index(region), region_token


def get_response_tokens(session, service_name, operation_model):
    """Output member names that carry pagination state, not data."""
    config = get_paginator_config(session, service_name, operation_model.name)
    if config is None:
        # The allowlist only has unpaginated commands without a model.
        return frozenset()
    tokens = {_AGGREGATED_RESUME_TOKEN}
    # Some services echo the input token, e.g. efs describe-file-systems.
    for key in ('output_token', 'input_token', 'more_results'):
        tokens.update(_as_list(config.get(key)))
    return frozenset(tokens)


def get_input_tokens(session, service_name, operation_model):
    """Input member names that resume pagination in one region."""
    config = get_paginator_config(session, service_name, operation_model.name)
    if config is None:
        return frozenset()
    return frozenset(_as_list(config.get('input_token')))


def pop_pagination_tokens(response, response_tokens):
    """Remove the tokens; return whether any of them had a value."""
    truncated = False
    for token in response_tokens:
        if response.pop(token, None):
            truncated = True
    return truncated


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def region_parameters(parameters, max_items, starting_token):
    """One region's parameters, with its own MaxItems and StartingToken."""
    if 'PaginationConfig' not in parameters:
        return parameters
    config = dict(parameters['PaginationConfig'])
    config.pop('StartingToken', None)
    if starting_token is not None:
        config['StartingToken'] = starting_token
    if max_items is not None:
        config['MaxItems'] = max_items
    return dict(parameters, PaginationConfig=config)


def with_next_token(responses, next_token, output):
    """The responses, then the multi-region token if there is one."""
    yield from responses
    if next_token and output == 'text':
        yield {'NextToken': {'NextToken': next_token[0]}}


def count_items(page_iterator, response):
    # botocore counts --max-items against the first result key.
    items = page_iterator.result_keys[0].search(response)
    return len(items) if items else 0
