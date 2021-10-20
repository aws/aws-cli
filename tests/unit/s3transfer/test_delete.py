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
from tests import BaseTaskTest
from s3transfer.delete import DeleteObjectTask


class TestDeleteObjectTask(BaseTaskTest):
    def setUp(self):
        super(TestDeleteObjectTask, self).setUp()
        self.bucket = 'mybucket'
        self.key = 'mykey'
        self.extra_args = {}
        self.callbacks = []

    def get_delete_task(self, **kwargs):
        default_kwargs = {
            'client': self.client, 'bucket': self.bucket, 'key': self.key,
            'extra_args': self.extra_args,
        }
        default_kwargs.update(kwargs)
        return self.get_task(DeleteObjectTask, main_kwargs=default_kwargs)

    def test_main(self):
        self.stubber.add_response(
            'delete_object', service_response={},
            expected_params={
                'Bucket': self.bucket, 'Key': self.key,
            }
        )
        task = self.get_delete_task()
        task()

        self.stubber.assert_no_pending_responses()

    def test_extra_args(self):
        self.extra_args['MFA'] = 'mfa-code'
        self.extra_args['VersionId'] = '12345'
        self.stubber.add_response(
            'delete_object', service_response={},
            expected_params={
                'Bucket': self.bucket, 'Key': self.key,
                # These extra_args should be injected into the
                # expected params for the delete_object call.
                'MFA': 'mfa-code',
                'VersionId': '12345',
            }
        )
        task = self.get_delete_task()
        task()

        self.stubber.assert_no_pending_responses()
