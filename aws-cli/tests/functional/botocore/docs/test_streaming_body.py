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
from botocore.docs.service import ServiceDocumenter

from tests import ALL_SERVICES
from tests.functional.botocore.docs import BaseDocsFunctionalTest


class TestStreamingBodyDocumentation(BaseDocsFunctionalTest):
    def test_all_streaming_body_are_properly_documented(self):
        for service_model in ALL_SERVICES:
            operations = [
                xform_name(operation)
                for operation in service_model.operation_names
                if service_model.operation_model(
                    operation
                ).has_streaming_output
            ]
            if not operations:
                continue
            service = service_model.service_name
            # Generate the complete service once, not once per streaming
            # operation. Each operation's documentation is still checked.
            ServiceDocumenter(
                service, self._session, self.root_services_path
            ).document_service()
            for operation in operations:
                self.assert_streaming_body_is_properly_documented(
                    service, operation
                )

    def assert_streaming_body_is_properly_documented(
        self, service, operation
    ):
        contents = self.get_client_method_contents(service, operation)
        method_docs = self.get_method_document_block(operation, contents)
        self.assert_contains_line('StreamingBody', method_docs)
