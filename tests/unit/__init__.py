# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from copy import deepcopy
import os
import re
import logging

import httpretty
import mock

from awscli.clidriver import create_clidriver


class BaseAWSCommandParamsTest(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        httpretty.enable()
        self.register_uri()
        self.last_params = {}
        # awscli/__init__.py injects AWS_DATA_PATH at import time
        # so that we can find cli.json.  This might be fixed in the
        # future, but for now we just grab that value out of the real
        # os.environ so the patched os.environ has this data and
        # the CLI works.
        self.environ = {
            'AWS_DATA_PATH': os.environ['AWS_DATA_PATH'],
            'AWS_DEFAULT_REGION': 'us-east-1',
            'AWS_ACCESS_KEY_ID': 'access_key',
            'AWS_SECRET_ACCESS_KEY': 'secret_key',
        }
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()

    def tearDown(self):
        httpretty.disable()
        self.environ_patch.stop()

    def register_uri(self):
        httpretty.register_uri(httpretty.POST, re.compile('.*'), body='')

    def before_call(self, params, **kwargs):
        self._store_params(params)

    def _store_params(self, params):
        self.last_params = deepcopy(params)

    def assert_params_for_cmd(self, cmd, params, expected_rc=0):
        logging.debug("Calling cmd: %s", cmd)
        driver = create_clidriver()
        driver.session.register('before-call', self.before_call)
        if not isinstance(cmd, list):
            cmdlist = cmd.split()
        else:
            cmdlist = cmd
        rc = driver.main(cmdlist)
        self.assertEqual(
            rc, expected_rc,
            "Unexpected rc (expected: %s, actual: %s) for command: %s" % (
                expected_rc, rc, cmd))
        self.assertDictEqual(params, self.last_params)
        return rc
