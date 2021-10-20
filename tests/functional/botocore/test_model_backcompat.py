# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os

from botocore.session import Session
from tests import ClientHTTPStubber
from tests.functional import TEST_MODELS_DIR


def test_old_model_continues_to_work():
    # This test ensures that botocore can load the service models as they exist
    # today.  There's a directory in tests/functional/models that is a
    # snapshot of a service model.  This test ensures that we can continue
    # to stub an API call using this model.  That way if the models ever
    # change we have a mechanism to ensure that the existing models continue
    # to work with botocore.  The test should not change (with the exception
    # of potential changes to the ClientHTTPStubber), and the files in
    # tests/functional/models should not change!
    session = Session()
    loader = session.get_component('data_loader')
    # We're adding our path to the existing search paths so we don't have to
    # copy additional data files such as _retry.json to our TEST_MODELS_DIR.
    # We only care about the service model and endpoints file not changing.
    # This also prevents us from having to make any changes to this models dir
    # if we end up adding a new data file that's needed to create clients.
    # We're adding our TEST_MODELS_DIR as the first element in the list to
    # ensure we load the endpoints.json file from TEST_MODELS_DIR.  For the
    # service model we have an extra safety net where we can choose a custom
    # client name.
    loader.search_paths.insert(0, TEST_MODELS_DIR)

    # The model dir we copied was renamed to 'custom-lambda'
    # to ensure we're loading our version of the model and not
    # the built in one.
    client = session.create_client(
        'custom-acm', region_name='us-west-2',
        aws_access_key_id='foo', aws_secret_access_key='bar',
    )
    with ClientHTTPStubber(client) as stubber:
        stubber.add_response(
            url='https://acm.us-west-2.amazonaws.com/',
            headers={'x-amzn-RequestId': 'abcd',
                     'Date': 'Fri, 26 Oct 2018 01:46:30 GMT',
                     'Content-Length': '29',
                     'Content-Type': 'application/x-amz-json-1.1'},
            body=b'{"CertificateSummaryList":[]}')
        response = client.list_certificates()
        assert response == {
            'CertificateSummaryList': [],
            'ResponseMetadata': {
                'HTTPHeaders': {
                    'content-length': '29',
                    'content-type': 'application/x-amz-json-1.1',
                    'date': 'Fri, 26 Oct 2018 01:46:30 GMT',
                    'x-amzn-requestid': 'abcd'},
                'HTTPStatusCode': 200,
                'RequestId': 'abcd',
                'RetryAttempts': 0}
        }

    # Also verify we can use the paginators as well.
    assert client.can_paginate('list_certificates') is True
    assert client.waiter_names == ['certificate_validated']
