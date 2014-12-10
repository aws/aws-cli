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
import mock
from awscli.compat import six

from awscli.customizations import preview
from awscli.testutils import BaseAWSCommandParamsTest


class TestPreviewMode(BaseAWSCommandParamsTest):

    def setUp(self):
        super(TestPreviewMode, self).setUp()
        self.stderr = six.StringIO()
        self.stderr_patch = mock.patch('sys.stderr', self.stderr)
        self.stderr_patch.start()
        self.full_config = {'profiles': {}}
        # Implementation detail, but we want to patch out the
        # session config, as that's the only way to control
        # preview services.
        self.driver.session._config=  self.full_config

    def tearDown(self):
        super(TestPreviewMode, self).tearDown()
        self.stderr_patch.stop()

    def test_invoke_preview_mode_service(self):
        # By default cloudfront is a preview service.
        # We check this to make sure we fail loudly if we
        # ever mark cloudfront as not being a preview service
        # by default.
        self.assertIn('cloudfront', preview.PREVIEW_SERVICES)
        rc = self.driver.main('cloudfront help'.split())
        self.assertEqual(rc, 1)
        self.assertIn(preview.PREVIEW_SERVICES['cloudfront'],
                      self.stderr.getvalue())

    @mock.patch('awscli.help.get_renderer')
    def test_preview_service_off(self, get_renderer):
        self.full_config['preview'] = {'cloudfront': 'true'}
        renderer = mock.Mock()
        get_renderer.return_value = renderer
        self.driver.main('cloudfront help'.split())
        # In this case, the normal help processing should have occurred
        # and we check that we rendered the contents.
        self.assertTrue(renderer.render.called)

    def test_preview_service_not_true(self):
        # If it's not "true" then we still make it a preview service.
        self.full_config['preview'] = {'cloudfront': 'false'}
        rc = self.driver.main('cloudfront help'.split())
        self.assertEqual(rc, 1)
        self.assertIn(preview.PREVIEW_SERVICES['cloudfront'],
                      self.stderr.getvalue())

    @mock.patch('awscli.help.get_renderer')
    def test_preview_mode_not_in_provider_help(self, renderer):
        self.driver.main(['help'])
        contents = renderer.return_value.render.call_args
        # The preview services should not be in the help output.
        for service in preview.PREVIEW_SERVICES:
            self.assertNotIn(service, contents)
