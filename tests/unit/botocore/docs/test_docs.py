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

from botocore.docs import generate_docs
from botocore.session import get_session
from tests import mock
from tests.unit.docs import BaseDocsTest


class TestGenerateDocs(BaseDocsTest):
    def setUp(self):
        super().setUp()
        self.loader_patch = mock.patch(
            'botocore.session.create_loader', return_value=self.loader
        )
        self.available_service_patch = mock.patch(
            'botocore.session.Session.get_available_services',
            return_value=['myservice'],
        )
        self.loader_patch.start()
        self.available_service_patch.start()

    def tearDown(self):
        super().tearDown()
        self.loader_patch.stop()
        self.available_service_patch.stop()

    def test_generate_docs(self):
        session = get_session()
        # Have the rst files get written to the temporary directory
        generate_docs(self.docs_root_dir, session)

        reference_service_path = os.path.join(
            self.root_services_path, 'myservice.rst'
        )
        self.assertTrue(os.path.exists(reference_service_path))

        # Make sure the rst file has some the expected contents.
        with open(reference_service_path) as f:
            contents = f.read()
            self.assertIn('AWS MyService', contents)
            self.assertIn('Client', contents)
            self.assertIn('Paginators', contents)
            self.assertIn('Waiters', contents)
