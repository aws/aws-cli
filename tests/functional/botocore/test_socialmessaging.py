# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import pytest
from botocore import xform_name
from botocore.session import get_session

_KNOWN_REPLACEMENTS = [
    'whatsapp',
]


def _get_all_xform_operations():
    session = get_session()
    service_model = session.get_service_model("socialmessaging")
    transform_operations = []
    for operation in service_model.operation_names:
        for replacement in _KNOWN_REPLACEMENTS:
            if replacement in operation.lower():
                transform_operations.append((operation, replacement))
    return transform_operations


XFORM_OPERATIONS = _get_all_xform_operations()


@pytest.mark.parametrize("operation, replacement", XFORM_OPERATIONS)
def test_known_replacements(operation, replacement):
    # Validates that if a replacement shows up in the lowercased version of an
    # operation, we will keep all of those characters together in the final operation
    # name
    assert replacement in xform_name(operation, '_')
    assert replacement in xform_name(operation, '-')
