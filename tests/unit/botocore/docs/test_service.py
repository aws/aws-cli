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
import os

from botocore.docs.service import ServiceDocumenter
from botocore.session import get_session
from tests import mock
from tests.unit.docs import BaseDocsTest


class TestServiceDocumenter(BaseDocsTest):
    def setUp(self):
        super().setUp()
        self.setup_documenter()

    def setup_documenter(self):
        self.add_shape_to_params('Biz', 'String')
        self.setup_client()
        with mock.patch(
            'botocore.session.create_loader', return_value=self.loader
        ):
            session = get_session()
            self.service_documenter = ServiceDocumenter(
                'myservice', session, self.root_services_path
            )

    def test_document_service(self):
        # Note that not everything will be included as it is just
        # a smoke test to make sure all the main parts are included.
        contents = self.service_documenter.document_service().decode('utf-8')
        lines = [
            '*********',
            'MyService',
            '*********',
            '======',
            'Client',
            '======',
            '.. py:class:: MyService.Client',
            '  A low-level client representing AWS MyService',
            '  AWS MyService Description',
            '    client = session.create_client(\'myservice\')',
            'These are the available methods:',
            '  myservice/client/sample_operation',
            '=================',
            'Client Exceptions',
            '=================',
            'Client exceptions are available on a client instance ',
            'via the ``exceptions`` property. For more detailed instructions ',
            'and examples on the exact usage of client exceptions, see the ',
            'error handling ',
            'Client exceptions are available',
            '==========',
            'Paginators',
            '==========',
            'Paginators are available on a client instance',
            'via the ``get_paginator`` method. For more detailed instructions ',
            'and examples on the usage of paginators, see the paginators',
            'The available paginators are:',
            '  myservice/paginator/SampleOperation',
            '=======',
            'Waiters',
            '=======',
            'Waiters are available on a client instance ',
            'via the ``get_waiter`` method. For more detailed instructions ',
            'and examples on the usage or waiters, see the waiters',
            '  myservice/waiter/SampleOperationComplete',
        ]
        for line in lines:
            self.assertIn(line, contents)

        self.assert_contains_lines_in_order(
            [
                '.. py:method:: MyService.Client.sample_operation(**kwargs)',
                '  **Examples**',
                '  Sample Description.',
                '  ::',
                '    response = client.sample_operation(',
            ],
            self.get_nested_service_contents(
                'myservice', 'client', 'sample_operation'
            ),
        )

    def test_document_service_no_paginator(self):
        os.remove(self.paginator_model_file)
        contents = self.service_documenter.document_service().decode('utf-8')
        self.assertNotIn('Paginators', contents)

    def test_document_service_no_waiter(self):
        os.remove(self.waiter_model_file)
        contents = self.service_documenter.document_service().decode('utf-8')
        self.assertNotIn('Waiters', contents)

    def test_document_service_no_context_params(self):
        contents = self.service_documenter.document_service().decode('utf-8')
        self.assertNotIn('Client Context Parameters', contents)

    def test_document_service_context_params(self):
        self.json_model['clientContextParams'] = {
            'ClientContextParam1': {
                'type': 'string',
                'documentation': 'A client context param',
            },
            'ClientContextParam2': {
                'type': 'boolean',
                'documentation': 'A second client context param',
            },
        }
        self.setup_documenter()
        contents = self.service_documenter.document_service().decode('utf-8')
        self.assertIn('Client Context Parameters', contents)
