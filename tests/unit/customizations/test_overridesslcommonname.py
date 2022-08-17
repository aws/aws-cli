# Copyright 2022 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

from awscli.testutils import create_clidriver
from awscli.customizations.overridesslcommonname import (
    update_endpoint_url,
    SSL_COMMON_NAMES,
)

import pytest
import argparse


def parameters():
    for service, regions in SSL_COMMON_NAMES.items():
        for region in regions:
            yield (service, region)


@pytest.fixture
def parsed_globals():
    pg = argparse.Namespace()
    pg.endpoint_url = None
    pg.region = None
    return pg


@pytest.fixture
def session():
    driver = create_clidriver()
    return driver.session


@pytest.mark.parametrize("service,region", parameters())
def test_update_endpoint_url(parsed_globals, session, service, region):
    parsed_globals.command = service
    session.set_config_variable("region", region)
    update_endpoint_url(session, parsed_globals)
    assert parsed_globals.endpoint_url == (
        f"https://{SSL_COMMON_NAMES[service][region]}"
    )


@pytest.mark.parametrize("service,region", parameters())
def test_url_modified_from_event(parsed_globals, session, service, region):
    assert parsed_globals.endpoint_url is None
    parsed_globals.command = service
    session.set_config_variable("region", region)
    session.emit(
        f"before-building-argument-table-parser.{service}",
        args=[],
        session=session,
        argument_table={},
        parsed_globals=parsed_globals,
    )
    assert parsed_globals.endpoint_url == (
        f"https://{SSL_COMMON_NAMES[service][region]}"
    )


def test_dont_modify_provided_url(parsed_globals, session):
    parsed_globals.endpoint_url = "http://test.com"
    parsed_globals.command = "sqs"
    update_endpoint_url(session, parsed_globals)
    assert parsed_globals.endpoint_url == "http://test.com"
