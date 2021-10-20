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
from botocore import xform_name
from tests.functional.docs import BaseDocsFunctionalTest
from botocore.docs.service import ServiceDocumenter


class TestStreamingBodyDocumentation(BaseDocsFunctionalTest):

    def test_all_streaming_body_are_properly_documented(self):
        for service in self._session.get_available_services():
            client = self._session.create_client(
                service, region_name='us-east-1',
                aws_access_key_id='foo', aws_secret_access_key='bar')
            service_model = client.meta.service_model
            for operation in service_model.operation_names:
                operation_model = service_model.operation_model(operation)
                if operation_model.has_streaming_output:
                    self.assert_streaming_body_is_properly_documented(
                        service, xform_name(operation))

    def assert_streaming_body_is_properly_documented(self, service, operation):
        service_docs = ServiceDocumenter(
            service, self._session).document_service()
        method_docs = self.get_method_document_block(operation, service_docs)
        self.assert_contains_line('StreamingBody', method_docs)
