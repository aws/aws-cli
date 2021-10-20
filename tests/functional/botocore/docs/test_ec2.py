# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from tests.functional.docs import BaseDocsFunctionalTest


class TestEc2Docs(BaseDocsFunctionalTest):
    def test_documents_encoding_of_user_data(self):
        docs = self.get_parameter_documentation_from_service(
            'ec2', 'run_instances', 'UserData')
        self.assertIn('base64 encoded automatically', docs.decode('utf-8'))

    def test_copy_snapshot_presigned_url_is_autopopulated(self):
        self.assert_is_documented_as_autopopulated_param(
            service_name='ec2',
            method_name='copy_snapshot',
            param_name='PresignedUrl')

    def test_copy_snapshot_destination_region_is_autopopulated(self):
        self.assert_is_documented_as_autopopulated_param(
            service_name='ec2',
            method_name='copy_snapshot',
            param_name='DestinationRegion')

    def test_idempotency_documented(self):
        content = self.get_docstring_for_method('ec2', 'purchase_scheduled_instances')
        # Client token should have had idempotentcy autopopulated doc appended
        self.assert_contains_line('This field is autopopulated if not provided',
                                  content)
