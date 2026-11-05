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
import dataclasses
import enum
from typing import Optional

from awscli.customizations.lambdaweb import constants


class EndpointAction(enum.Enum):
    """How deploy handles an existing Web Function's endpoint.

    New Web Function creation includes the initial endpoint and does not use
    an endpoint action plan.
    """

    ADD = 'add'
    """``--endpoint-name`` identifies an endpoint that does not exist.

    The command confirms creation before deployment and creates the endpoint
    after the revision becomes Active.
    """

    UPDATE = 'update'
    """A target endpoint exists.

    The command points it at the new revision and applies any requested
    mutable settings.
    """

    NONE = 'none'
    """An existing Web Function has no endpoints and none was named.

    The command deploys the revision without creating an endpoint.
    """


@dataclasses.dataclass
class EndpointPlan:
    action: EndpointAction
    target: Optional[dict] = None
    """The live endpoint summary the plan acts on, or ``None`` when there is
    nothing to act on yet (``ADD`` / ``NONE``)."""


def resolve_endpoint_plan(lambda_web, parsed_args):
    """Decide what to do with the function's endpoint on the update path.

    An explicit ``--endpoint-name`` wins. Otherwise, prefer an auto-deploying
    endpoint, and then fall back to the first endpoint.
    """
    endpoints = _list_endpoints(lambda_web, parsed_args.name)
    by_name = {e.get('endpointName'): e for e in endpoints}

    if parsed_args.endpoint_name:
        target = by_name.get(parsed_args.endpoint_name)
        if target is None:
            return EndpointPlan(EndpointAction.ADD)
        return EndpointPlan(EndpointAction.UPDATE, target)

    if not endpoints:
        return EndpointPlan(EndpointAction.NONE)
    auto = next(
        (
            e
            for e in endpoints
            if e.get('autoDeploymentMode')
            == constants.AUTO_DEPLOY_LATEST_REVISION
        ),
        None,
    )
    return EndpointPlan(EndpointAction.UPDATE, auto or endpoints[0])


def _list_endpoints(lambda_web, function_name):
    """Return every endpoint across all response pages."""
    endpoints = []
    request = {'functionName': function_name}
    while True:
        response = lambda_web.list_web_function_endpoints(**request)
        endpoints.extend(response.get('endpoints') or [])
        next_token = response.get('nextToken')
        if not next_token:
            return endpoints
        request['nextToken'] = next_token


# Message fragments that identify an optimistic-concurrency conflict.
_ENDPOINT_UPDATE_CONFLICT_SIGNATURES = ('newer update', 'versionid')


def is_endpoint_update_conflict(error):
    """Return True for a retryable ``UpdateWebFunctionEndpoint`` race conflict.

    Other ``ConflictException`` causes are not retried: retrying would fail the
    same way and hide the real reason.
    """
    err = error.response.get('Error', {})
    if err.get('Code') != 'ConflictException':
        return False
    message = (err.get('Message') or '').lower()
    return any(sig in message for sig in _ENDPOINT_UPDATE_CONFLICT_SIGNATURES)
