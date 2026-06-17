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
from botocore.docs.client import ClientContextParamsDocumenter
from botocore.docs.service import ServiceDocumenter
from tests.functional.docs import BaseDocsFunctionalTest


class TestS3Docs(BaseDocsFunctionalTest):
    def test_auto_populates_sse_customer_key_md5(self):
        self.assert_is_documented_as_autopopulated_param(
            service_name='s3',
            method_name='put_object',
            param_name='SSECustomerKeyMD5',
        )

    def test_auto_populates_copy_source_sse_customer_key_md5(self):
        self.assert_is_documented_as_autopopulated_param(
            service_name='s3',
            method_name='copy_object',
            param_name='CopySourceSSECustomerKeyMD5',
        )

    def test_hides_content_md5_when_impossible_to_provide(self):
        modified_methods = [
            'delete_objects',
            'put_bucket_acl',
            'put_bucket_cors',
            'put_bucket_lifecycle',
            'put_bucket_logging',
            'put_bucket_policy',
            'put_bucket_notification',
            'put_bucket_tagging',
            'put_bucket_replication',
            'put_bucket_website',
            'put_bucket_request_payment',
            'put_object_acl',
            'put_bucket_versioning',
        ]
        ServiceDocumenter(
            's3', self._session, self.root_services_path
        ).document_service()
        for method_name in modified_methods:
            contents = self.get_client_method_contents('s3', method_name)
            method_contents = self.get_method_document_block(
                method_name, contents
            )
            self.assertNotIn(
                'ContentMD5=\'string\'', method_contents.decode('utf-8')
            )

    def test_generate_presigned_url_documented(self):
        content = self.get_docstring_for_method('s3', 'generate_presigned_url')
        self.assert_contains_line('generate_presigned_url', content)

    def test_copy_source_documented_as_union_type(self):
        content = self.get_docstring_for_method('s3', 'copy_object')
        dict_form = (
            "{'Bucket': 'string', 'Key': 'string', 'VersionId': 'string'}"
        )
        self.assert_contains_line(
            f"CopySource='string' or {dict_form}", content
        )

    def test_copy_source_param_docs_also_modified(self):
        content = self.get_docstring_for_method('s3', 'copy_object')
        param_docs = self.get_parameter_document_block('CopySource', content)
        # We don't want to overspecify the test, so I've picked
        # an arbitrary line from the customized docs.
        self.assert_contains_line(
            "You can also provide this value as a dictionary", param_docs
        )

    def test_s3_context_params_omitted(self):
        omitted_params = ClientContextParamsDocumenter.OMITTED_CONTEXT_PARAMS
        s3_omitted_params = omitted_params['s3']
        content = ServiceDocumenter(
            's3', self._session, self.root_services_path
        ).document_service()
        for param in s3_omitted_params:
            param_name = f'``{xform_name(param)}``'
            self.assert_not_contains_line(param_name, content)

    def test_s3control_context_params_omitted(self):
        omitted_params = ClientContextParamsDocumenter.OMITTED_CONTEXT_PARAMS
        s3control_omitted_params = omitted_params['s3control']
        content = ServiceDocumenter(
            's3control', self._session, self.root_services_path
        ).document_service()
        for param in s3control_omitted_params:
            param_name = f'``{xform_name(param)}``'
            self.assert_not_contains_line(param_name, content)
