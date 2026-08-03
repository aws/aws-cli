# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from unittest.mock import patch

from botocore.parsers import RestJSONParser
from botocore.session import Session
from botocore.utils import PRIORITY_ORDERED_SUPPORTED_PROTOCOLS
from tests import ClientHTTPStubber
from tests.functional import TEST_MODELS_DIR


def test_correct_protocol_selection():
    # This test ensures that botocore can properly resolve a protocol and
    # apply that to both the serializer and parser.  The logic for protocol
    # selection is deserialized for picking the serializer and parser, so
    # we add this test to make sure that in at least a simple circumstance
    # where a protocol is selected that is not the same as the "protocol"
    # trait, that we can properly create and use a serializer/parser.
    session = Session()
    loader = session.get_component('data_loader')
    loader.search_paths.insert(0, TEST_MODELS_DIR)

    client = session.create_client(
        'test-protocol-list',
        region_name='us-west-2',
        aws_access_key_id='foo',
        aws_secret_access_key='bar',
    )

    # This test would not be effective if the `protocol` trait was ever
    # a higher priority protocol than the resolved protocol as it would
    # pass even if a client's resolved parser was based on the `protocol`
    # trait instead of the resolved protocol
    service_model = client.meta.service_model
    assert PRIORITY_ORDERED_SUPPORTED_PROTOCOLS.index(
        service_model.protocol
    ) > PRIORITY_ORDERED_SUPPORTED_PROTOCOLS.index(
        service_model.resolved_protocol
    )

    original_do_parse = RestJSONParser._do_parse

    def tracking_do_parse(self, *args, **kwargs):
        called['was_called'] = True
        return original_do_parse(self, *args, **kwargs)

    with patch("botocore.parsers.RestJSONParser._do_parse", tracking_do_parse):
        called = {'was_called': False}
        with ClientHTTPStubber(client) as stubber:
            stubber.add_response(
                body=b'{"Bar": "Baz"}',
            )
            response = client.test_protocol_selection(Foo="input")
            assert response['Bar'] == 'Baz'
        assert called['was_called'], (
            "_do_parse was not called on RestJSONParser as expected"
        )
