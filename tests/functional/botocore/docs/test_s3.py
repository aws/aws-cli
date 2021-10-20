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
from botocore.docs.service import ServiceDocumenter


class TestS3Docs(BaseDocsFunctionalTest):
    def test_auto_populates_sse_customer_key_md5(self):
        self.assert_is_documented_as_autopopulated_param(
            service_name='s3',
            method_name='put_object',
            param_name='SSECustomerKeyMD5')

    def test_auto_populates_copy_source_sse_customer_key_md5(self):
        self.assert_is_documented_as_autopopulated_param(
            service_name='s3',
            method_name='copy_object',
            param_name='CopySourceSSECustomerKeyMD5')

    def test_hides_content_md5_when_impossible_to_provide(self):
        modified_methods = ['delete_objects', 'put_bucket_acl',
                            'put_bucket_cors', 'put_bucket_lifecycle',
                            'put_bucket_logging', 'put_bucket_policy',
                            'put_bucket_notification', 'put_bucket_tagging',
                            'put_bucket_replication', 'put_bucket_website',
                            'put_bucket_request_payment', 'put_object_acl',
                            'put_bucket_versioning']
        service_contents = ServiceDocumenter(
            's3', self._session).document_service()
        for method_name in modified_methods:
            method_contents = self.get_method_document_block(
                method_name, service_contents)
            self.assertNotIn('ContentMD5=\'string\'',
                             method_contents.decode('utf-8'))

    def test_copy_source_documented_as_union_type(self):
        content  = self.get_docstring_for_method('s3', 'copy_object')
        dict_form = (
            "{'Bucket': 'string', 'Key': 'string', 'VersionId': 'string'}")
        self.assert_contains_line(
            "CopySource='string' or %s" % dict_form, content)

    def test_copy_source_param_docs_also_modified(self):
        content  = self.get_docstring_for_method('s3', 'copy_object')
        param_docs = self.get_parameter_document_block('CopySource', content)
        # We don't want to overspecify the test, so I've picked
        # an arbitrary line from the customized docs.
        self.assert_contains_line(
            "You can also provide this value as a dictionary", param_docs)
