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
import json
import os
import shutil
import tempfile

from botocore.docs.service import ServiceDocumenter

from tests.functional.botocore.docs import BaseDocsFunctionalTest


def _undocumented_input_members():
    # None of these members have documentation, so the request params
    # documenter has no doc string to write for them.
    return {
        'Bucket': {
            'shape': 'String',
            'location': 'uri',
            'locationName': 'Bucket',
        },
        'Key': {
            'shape': 'String',
            'location': 'uri',
            'locationName': 'Key',
        },
        'CopySource': {
            'shape': 'String',
            'location': 'header',
            'locationName': 'x-amz-copy-source',
        },
        'SSECustomerKeyMD5': {
            'shape': 'String',
            'location': 'header',
            'locationName': 'x-amz-server-side-encryption-customer-key-MD5',
        },
        'CopySourceSSECustomerKeyMD5': {
            'shape': 'String',
            'location': 'header',
            'locationName': (
                'x-amz-copy-source-server-side-encryption-customer-key-MD5'
            ),
        },
    }


SERVICE_NAME = 'synthetic-s3'

SYNTHETIC_S3_MODEL = {
    'version': '2.0',
    'metadata': {
        'apiVersion': '2006-03-01',
        'endpointPrefix': 's3',
        'protocol': 'rest-xml',
        'serviceFullName': 'Amazon Simple Storage Service',
        'serviceId': 'S3',
        'signatureVersion': 's3v4',
        'uid': 's3-2006-03-01',
    },
    'operations': {
        'CopyObject': {
            'name': 'CopyObject',
            'http': {'method': 'PUT', 'requestUri': '/{Bucket}/{Key+}'},
            'input': {'shape': 'CopyObjectRequest'},
            'output': {'shape': 'EmptyOutput'},
        },
        'SampleCopyOperation': {
            'name': 'SampleCopyOperation',
            'http': {'method': 'POST', 'requestUri': '/{Bucket}/{Key+}'},
            'input': {'shape': 'SampleCopyOperationRequest'},
            'output': {'shape': 'EmptyOutput'},
        },
    },
    'shapes': {
        'CopyObjectRequest': {
            'type': 'structure',
            'required': ['Bucket', 'Key', 'CopySource'],
            'members': _undocumented_input_members(),
        },
        'SampleCopyOperationRequest': {
            'type': 'structure',
            'required': ['Bucket', 'Key', 'CopySource'],
            'members': _undocumented_input_members(),
        },
        'EmptyOutput': {'type': 'structure', 'members': {}},
        'String': {'type': 'string'},
    },
}

ENDPOINT_RULE_SET = {
    'version': '1.3',
    'parameters': {},
    'rules': [
        {
            'conditions': [],
            'endpoint': {
                'url': 'https://s3.amazonaws.com',
                'properties': {},
                'headers': {},
            },
            'type': 'endpoint',
        }
    ],
}


class TestUndocumentedRequestMembers(BaseDocsFunctionalTest):
    def setUp(self):
        super().setUp()
        self.models_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.models_dir)
        # Use a separate service name so that none of the real S3 model
        # files (paginators, waiters, sdk-extras) are loaded alongside the
        # synthetic model. The service ID is still S3, so the S3 docs
        # handlers are registered for it.
        model_dir = os.path.join(self.models_dir, SERVICE_NAME, '2006-03-01')
        os.makedirs(model_dir)
        model_files = {
            'service-2.json': SYNTHETIC_S3_MODEL,
            'endpoint-rule-set-1.json': ENDPOINT_RULE_SET,
        }
        for filename, model in model_files.items():
            with open(os.path.join(model_dir, filename), 'w') as f:
                json.dump(model, f)
        loader = self._session.get_component('data_loader')
        loader.search_paths.insert(0, self.models_dir)

    def document_service(self):
        return ServiceDocumenter(
            SERVICE_NAME, self._session, self.root_services_path
        ).document_service()

    def get_param_block(self, method_name, param_name):
        contents = self.get_client_method_contents(SERVICE_NAME, method_name)
        method_contents = self.get_method_document_block(method_name, contents)
        return self.get_parameter_document_block(param_name, method_contents)

    def test_documents_service_with_undocumented_members(self):
        contents = self.document_service()
        self.assert_contains_line('copy_object', contents)
        self.assert_contains_line('sample_copy_operation', contents)

    def test_auto_populated_note_for_undocumented_members(self):
        self.document_service()
        for method_name in ['copy_object', 'sample_copy_operation']:
            for param_name in [
                'SSECustomerKeyMD5',
                'CopySourceSSECustomerKeyMD5',
            ]:
                param_contents = self.get_param_block(method_name, param_name)
                self.assert_not_contains_line('REQUIRED', param_contents)
                self.assert_contains_line(
                    'Please note that this parameter is automatically '
                    'populated',
                    param_contents,
                )

    def test_copy_source_form_for_undocumented_member(self):
        self.document_service()
        param_contents = self.get_param_block('copy_object', 'CopySource')
        self.assert_contains_line(
            ':type CopySource: str or dict', param_contents
        )
        self.assert_contains_line(
            'You can also provide this value as a dictionary', param_contents
        )
