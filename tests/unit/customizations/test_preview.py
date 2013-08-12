# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from tests import unittest

import mock
import six

from awscli.customizations import preview
from awscli.clidriver import create_clidriver
from tests.unit import BaseAWSCommandParamsTest


class TestPreviewMode(BaseAWSCommandParamsTest):

    def setUp(self):
        super(TestPreviewMode, self).setUp()
        self.stderr = six.StringIO()
        self.stderr_patch = mock.patch('sys.stderr', self.stderr)
        self.stderr_patch.start()
        self.driver = create_clidriver()
        self.full_config = {}
        # Implementation detail, but we want to patch out the
        # session config, as that's the only way to control
        # preview services.
        self.driver.session._config = self.full_config

    def tearDown(self):
        super(TestPreviewMode, self).tearDown()
        self.stderr_patch.stop()

    def test_invoke_preview_mode_service(self):
        # By default cloudsearch is a preview service.
        # We check this to make sure we fail loudly if we
        # ever mark cloudsearch as not being a preview service
        # by default.
        self.assertIn('cloudsearch', preview.PREVIEW_SERVICES)
        rc = self.driver.main('cloudsearch help'.split())
        self.assertEqual(rc, 1)
        self.assertIn(preview.PREVIEW_SERVICES['cloudsearch'],
                      self.stderr.getvalue())

    @mock.patch('awscli.help.get_renderer')
    def test_preview_service_off(self, get_renderer):
        self.full_config['preview'] = {'cloudsearch': 'true'}
        renderer = mock.Mock()
        get_renderer.return_value = renderer
        rc = self.driver.main('cloudsearch help'.split())
        # In this case, the normal help processing should have occurred
        # and we check that we rendered the contents.
        self.assertTrue(renderer.render.called)

    def test_preview_service_not_true(self):
        # If it's not "true" then we still make it a preview service.
        self.full_config['preview'] = {'cloudsearch': 'false'}
        rc = self.driver.main('cloudsearch help'.split())
        self.assertEqual(rc, 1)
        self.assertIn(preview.PREVIEW_SERVICES['cloudsearch'],
                      self.stderr.getvalue())
