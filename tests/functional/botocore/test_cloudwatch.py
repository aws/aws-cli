# Copyright 2026 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore.stub import Stubber

_OTEL_OPERATIONS = [
    'GetOTelEnrichment',
    'StartOTelEnrichment',
    'StopOTelEnrichment',
]


@pytest.mark.validates_models
@pytest.mark.parametrize("operation", _OTEL_OPERATIONS)
def test_otel_xform_name(operation):
    assert 'otel' in xform_name(operation, '_')
    assert 'otel' in xform_name(operation, '-')


class TestCloudWatchOTelEnrichment:
    def setup_method(self):
        session = get_session()
        self.client = session.create_client('cloudwatch', 'us-east-1')
        self.stubber = Stubber(self.client)
        self.stubber.activate()

    @pytest.mark.parametrize(
        "old_name, new_name, response",
        [
            (
                'get_o_tel_enrichment',
                'get_otel_enrichment',
                {'Status': 'Running'},
            ),
            ('start_o_tel_enrichment', 'start_otel_enrichment', {}),
            ('stop_o_tel_enrichment', 'stop_otel_enrichment', {}),
        ],
    )
    def test_otel_enrichment_aliased(self, old_name, new_name, response):
        self.stubber.add_response(new_name, response)
        self.stubber.add_response(new_name, response)

        getattr(self.client, old_name)()
        getattr(self.client, new_name)()

        self.stubber.assert_no_pending_responses()
