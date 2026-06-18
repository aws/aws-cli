# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import re

import pytest

from botocore.session import get_session

BLOCKLIST = []

# Service names are limited here to 50 characters here as that seems like a
# reasonable limit in the general case. Services can be added to the
# blacklist above to be given an exception.
VALID_NAME_REGEX = re.compile(
    (
        '[a-z]'  # Starts with a letter
        '[a-z0-9]*'  # Followed by any number of letters or digits
        '(-[a-z0-9]+)*$'  # Dashes are allowed as long as they aren't
        # consecutive or at the end
    ),
    re.M,
)
VALID_NAME_EXPLANATION = (
    'Service names must be made up entirely of lowercase alphanumeric '
    'characters and dashes. The name must start with a letter and may not end '
    'with a dash'
)
MIN_NAME_LENGTH_EXPLANATION = (
    'Service name must be greater than or equal to 2 characters in length.'
)
MAX_NAME_LENGTH_EXPLANATION = (
    'Service name must be less than or equal to 50 characters in length.'
)
MIN_SERVICE_NAME_LENGTH = 2
MAX_SERVICE_NAME_LENGTH = 50


def _service_names():
    session = get_session()
    loader = session.get_component('data_loader')
    return loader.list_available_services('service-2')


@pytest.mark.parametrize("service_name", _service_names())
def test_service_names_are_valid_length(service_name):
    if service_name not in BLOCKLIST:
        service_name_length = len(service_name)
        is_not_too_short = service_name_length >= MIN_SERVICE_NAME_LENGTH
        is_not_too_long = service_name_length <= MAX_SERVICE_NAME_LENGTH

        assert is_not_too_short, MIN_NAME_LENGTH_EXPLANATION
        assert is_not_too_long, MAX_NAME_LENGTH_EXPLANATION


@pytest.mark.parametrize("service_name", _service_names())
def test_service_names_are_valid_pattern(service_name):
    if service_name not in BLOCKLIST:
        valid = VALID_NAME_REGEX.match(service_name) is not None
        assert valid, VALID_NAME_EXPLANATION
