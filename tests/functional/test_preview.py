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
from awscli.customizations import preview
from awscli.compat import StringIO
from awscli.testutils import mock, BaseAWSCommandParamsTest


class TestPreviewMode(BaseAWSCommandParamsTest):

    def setUp(self):
        super(TestPreviewMode, self).setUp()
        self.stderr = StringIO()
        self.stderr_patch = mock.patch('sys.stderr', self.stderr)
        self.stderr_patch.start()
        self.full_config = {'profiles': {}}
        # Implementation detail, but we want to patch out the
        # session config, as that's the only way to control
        # preview services.
        self.driver.session._config = self.full_config

    def tearDown(self):
        super(TestPreviewMode, self).tearDown()
        self.stderr_patch.stop()

    def test_invoke_preview_mode_service(self):
        # By default cloudfront is a preview service.
        # We check this to make sure we fail loudly if we
        # ever mark cloudfront as not being a preview service
        # by default.
        self.assertIn('sdb', preview.PREVIEW_SERVICES)
        rc = self.driver.main('sdb list-domains'.split())
        self.assertEqual(rc, 1)
        self.assertIn(preview.PreviewModeCommandMixin.HELP_SNIPPET,
                      self.stderr.getvalue())

    def test_preview_service_not_true(self):
        # If it's not "true" then we still make it a preview service.
        self.full_config['preview'] = {'sdb': 'false'}
        rc = self.driver.main('sdb list-domains'.split())
        self.assertEqual(rc, 1)
        self.assertIn(preview.PreviewModeCommandMixin.HELP_SNIPPET,
                      self.stderr.getvalue())

    def test_preview_service_enabled_makes_call(self):
        self.full_config['preview'] = {'sdb': 'true'}
        self.assert_params_for_cmd('sdb list-domains', params={})

    @mock.patch('awscli.help.get_renderer')
    def test_can_still_document_preview_service(self, get_renderer):
        # Even if a service is still marked as being in preview,
        # you can still pull up its documentation.
        self.full_config['preview'] = {'sdb': 'false'}
        self.driver.main('sdb help'.split())
        # In this case, the normal help processing should have occurred
        # and we check that we rendered the contents correctly.
        self.assertTrue(get_renderer.return_value.render.called)
        contents = get_renderer.return_value.render.call_args[0][0]
        self.assertIn('aws configure set preview.sdb true',
                      contents.decode('utf-8'))

    @mock.patch('awscli.help.get_renderer')
    def test_document_preview_service_operation(self, get_renderer):
        # Even if a service is still marked as being in preview,
        # you can still pull up its documentation for its operations.
        self.full_config['preview'] = {'sdb': 'false'}
        self.driver.main('sdb list-domains help'.split())
        # The contents should be have the correct way to set the command
        # out of preview in the config file.
        self.assertTrue(get_renderer.return_value.render.called)
        contents = get_renderer.return_value.render.call_args[0][0]
        self.assertIn('aws configure set preview.sdb true',
                      contents.decode('utf-8'))

    @mock.patch('awscli.help.get_renderer')
    def test_preview_mode_is_in_provider_help(self, renderer):
        self.driver.main(['help'])
        contents = renderer.return_value.render.call_args[0][0]
        # The preview services should still be in the help output.
        for service in preview.PREVIEW_SERVICES:
            self.assertIn(service, contents.decode('utf-8'))
