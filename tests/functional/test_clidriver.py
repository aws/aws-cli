# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import os
import re
import shutil
import functools

from tests import RawResponse

import mock

import botocore
from botocore.session import Session

from awscli.testutils import FileCreator
from awscli.testutils import BaseCLIDriverTest
from awscli.clidriver import create_clidriver


class RegionCapture(object):
    def __init__(self):
        self.region = None

    def __call__(self, request, **kwargs):
        url = request.url
        region = re.match(
            'https://.*?\.(.*?)\.amazonaws\.com', url).groups(1)[0]
        self.region = region


class TestSession(BaseCLIDriverTest):
    def setUp(self):
        super(TestSession, self).setUp()
        urllib3_session_send = 'botocore.httpsession.URLLib3Session.send'
        self._urllib3_patch = mock.patch(urllib3_session_send)
        self._send = self._urllib3_patch.start()
        self._send.side_effect = self.get_response
        self._responses = []

    def tearDown(self):
        self._urllib3_patch.stop()

    def get_response(self, request):
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def add_response(self, body, status_code=200):
        response = botocore.awsrequest.AWSResponse(
            url='http://169.254.169.254/',
            status_code=status_code,
            headers={},
            raw=RawResponse(body)
        )
        self._responses.append(response)

    def test_imds_region_is_used_as_fallback_wo_v2_support(self):
        # Remove region override from the environment variables.
        self.environ.pop('AWS_DEFAULT_REGION', 0)
        # First response should be from the IMDS server for security token
        # if server supports IMDSv1 only there will be no response for token
        self.add_response(None)
        # Then another response from the IMDS server for an availibility
        # zone.
        self.add_response(b'us-mars-2a')
        # Once a region is fetched form the IMDS server we need to mock an
        # XML response from ec2 so that the CLI driver doesn't throw an error
        # during parsing.
        self.add_response(
            b'<?xml version="1.0" ?><foo><bar>text</bar></foo>')
        capture = RegionCapture()
        self.session.register('before-send.ec2.*', capture)
        self.driver.main(['ec2', 'describe-instances'])
        self.assertEqual(capture.region, 'us-mars-2')

    def test_imds_region_is_used_as_fallback_with_v2_support(self):
        # Remove region override from the environment variables.
        self.environ.pop('AWS_DEFAULT_REGION', 0)
        # First response should be from the IMDS server for security token
        # if server supports IMDSv2 it'll return token
        self.add_response(b'token')
        # Then another response from the IMDS server for an availibility
        # zone.
        self.add_response(b'us-mars-2a')
        # Once a region is fetched form the IMDS server we need to mock an
        # XML response from ec2 so that the CLI driver doesn't throw an error
        # during parsing.
        self.add_response(
            b'<?xml version="1.0" ?><foo><bar>text</bar></foo>')
        capture = RegionCapture()
        self.session.register('before-send.ec2.*', capture)
        self.driver.main(['ec2', 'describe-instances'])
        self.assertEqual(capture.region, 'us-mars-2')


class TestPlugins(BaseCLIDriverTest):
    def setUp(self):
        super(TestPlugins, self).setUp()
        self.files = FileCreator()
        self.plugins_site_packages = os.path.join(
            self.files.rootdir, 'site-packages'
        )
        self.plugin_module_name = 'add_awscli_cmd_plugin'
        self.plugin_filename = os.path.join(
            os.path.dirname(__file__), self.plugin_module_name) + '.py'
        self.setup_plugin_site_packages()

    def setup_plugin_site_packages(self):
        os.makedirs(self.plugins_site_packages)
        shutil.copy(self.plugin_filename, self.plugins_site_packages)

    def tearDown(self):
        super(TestPlugins, self).tearDown()
        self.files.remove_all()

    def assert_plugin_loaded(self, clidriver):
        self.assertIn('plugin-test-cmd', clidriver.subcommand_table)

    def assert_plugin_not_loaded(self, clidriver):
        self.assertNotIn('plugin-test-cmd', clidriver.subcommand_table)

    def create_config(self, config_contents):
        config_file = self.files.create_file('config', config_contents)
        self.environ['AWS_CONFIG_FILE'] = config_file

    def test_plugins_loaded_from_specified_path(self):
        self.create_config(
            '[plugins]\n'
            'cli_legacy_plugin_path = %s\n'
            'myplugin = %s\n' % (
                self.plugins_site_packages, self.plugin_module_name)
        )
        clidriver = create_clidriver()
        self.assert_plugin_loaded(clidriver)

    def test_plugins_are_not_loaded_when_path_specified(self):
        self.create_config(
            '[plugins]\n'
            'myplugin = %s\n' % self.plugin_module_name
        )
        clidriver = create_clidriver()
        self.assert_plugin_not_loaded(clidriver)

    def test_looks_in_all_specified_paths(self):
        nonexistent_dir = os.path.join(
            self.files.rootdir, 'no-exist'
        )
        plugin_path = os.pathsep.join(
            [nonexistent_dir, self.plugins_site_packages])
        self.create_config(
            '[plugins]\n'
            'cli_legacy_plugin_path = %s\n'
            'myplugin = %s\n' % (plugin_path, self.plugin_module_name)
        )
        clidriver = create_clidriver()
        self.assert_plugin_loaded(clidriver)
