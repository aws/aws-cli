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

import mock

from tests.unit.docs import BaseDocsTest
from botocore.session import get_session
from botocore.docs.service import ServiceDocumenter


class TestServiceDocumenter(BaseDocsTest):
    def setUp(self):
        super(TestServiceDocumenter, self).setUp()
        self.add_shape_to_params('Biz', 'String')
        self.setup_client()
        with mock.patch('botocore.session.create_loader',
                        return_value=self.loader):
            session = get_session()
            self.service_documenter = ServiceDocumenter(
                'myservice', session)

    def test_document_service(self):
        # Note that not everything will be included as it is just
        # a smoke test to make sure all of the main parts are inluded.
        contents = self.service_documenter.document_service().decode('utf-8')
        lines = [
            '*********',
            'MyService',
            '*********',
            '.. contents:: Table of Contents',
            '   :depth: 2',
            '======',
            'Client',
            '======',
            '.. py:class:: MyService.Client',
            '  A low-level client representing AWS MyService',
            '  AWS MyService Description',
            '    client = session.create_client(\'myservice\')',
            '  These are the available methods:',
            '  *   :py:meth:`~MyService.Client.sample_operation`',
            '  .. py:method:: sample_operation(**kwargs)',
            '    **Examples** ',
            '    Sample Description.',
            '    ::',
            '      response = client.sample_operation(',
            '=================',
            'Client Exceptions',
            '=================',
            'Client exceptions are available',
            '==========',
            'Paginators',
            '==========',
            '.. py:class:: MyService.Paginator.SampleOperation',
            '  .. py:method:: paginate(**kwargs)',
            '=======',
            'Waiters',
            '=======',
            '.. py:class:: MyService.Waiter.SampleOperationComplete',
            '  .. py:method:: wait(**kwargs)'
        ]
        for line in lines:
            self.assertIn(line, contents)

    def test_document_service_no_paginator(self):
        os.remove(self.paginator_model_file)
        contents = self.service_documenter.document_service().decode('utf-8')
        self.assertNotIn('Paginators', contents)

    def test_document_service_no_waiter(self):
        os.remove(self.waiter_model_file)
        contents = self.service_documenter.document_service().decode('utf-8')
        self.assertNotIn('Waiters', contents)
