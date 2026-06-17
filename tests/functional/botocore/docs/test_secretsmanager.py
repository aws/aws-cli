# Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from botocore.docs.service import ServiceDocumenter
from tests.functional.docs import BaseDocsFunctionalTest


class TestSecretsManagerDocs(BaseDocsFunctionalTest):
    def test_generate_presigned_url_is_not_documented(self):
        documenter = ServiceDocumenter(
            'secretsmanager', self._session, self.root_services_path
        )
        docs = documenter.document_service()
        self.assert_not_contains_line('generate_presigned_url', docs)
