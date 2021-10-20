# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore.stub import Stubber
from tests import BaseSessionTest


class TestMturk(BaseSessionTest):
    def setUp(self):
        super(TestMturk, self).setUp()
        self.region = 'us-west-2'
        self.client = self.session.create_client(
            'mturk', self.region)
        self.stubber = Stubber(self.client)
        self.stubber.activate()

    def tearDown(self):
        self.stubber.deactivate()

    def test_list_hits_aliased(self):
        self.stubber.add_response('list_hits_for_qualification_type', {})
        self.stubber.add_response('list_hits_for_qualification_type', {})

        params = {'QualificationTypeId': 'foo'}

        self.client.list_hi_ts_for_qualification_type(**params)
        self.client.list_hits_for_qualification_type(**params)

        self.stubber.assert_no_pending_responses()
