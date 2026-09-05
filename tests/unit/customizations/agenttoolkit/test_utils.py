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
from argparse import Namespace
from unittest.mock import MagicMock

from awscli.customizations.agenttoolkit.utils import (
    AGENT_TOOLKIT_REGION,
    create_client,
)


def _create_client(region):
    session = MagicMock()
    parsed_globals = Namespace(region=region)
    create_client(session, parsed_globals)
    return session.create_client.call_args


def test_defaults_region_when_none_configured():
    args = _create_client(region=None)
    assert args.kwargs['region_name'] == AGENT_TOOLKIT_REGION


def test_honors_explicit_region():
    args = _create_client(region='us-west-2')
    assert args.kwargs.get('region_name') == 'us-west-2'
