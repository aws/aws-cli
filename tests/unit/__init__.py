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
from tests import unittest, create_clidriver
import os
import copy
import logging
import tempfile
import shutil

import mock
import six
from botocore.vendored import requests


class BaseAWSCommandParamsTest(unittest.TestCase):
    maxDiff = None

    def setUp(self):
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
        self.http_response = requests.models.Response()
        self.http_response.status_code = 200
        self.parsed_response = {}
        self.make_request_patch = mock.patch('botocore.endpoint.Endpoint.make_request')
        self.make_request_is_patched = False
        self.operations_called = []
        self.parsed_responses = None
        self.driver = create_clidriver()

    def tearDown(self):
        # This clears all the previous registrations.
        self.environ_patch.stop()
        if self.make_request_is_patched:
            self.make_request_patch.stop()

    def before_call(self, params, **kwargs):
        self._store_params(params)

    def _store_params(self, params):
        self.last_params = params

    def patch_make_request(self):
        make_request_patch = self.make_request_patch.start()
        if self.parsed_responses is not None:
            make_request_patch.side_effect = lambda *args, **kwargs: \
                (self.http_response, self.parsed_responses.pop(0))
        else:
            make_request_patch.return_value = (self.http_response, self.parsed_response)
        self.make_request_is_patched = True

    def assert_params_for_cmd(self, cmd, params=None, expected_rc=0,
                              stderr_contains=None, ignore_params=None):
        stdout, stderr, rc = self.run_cmd(cmd, expected_rc)
        if stderr_contains is not None:
            self.assertIn(stderr_contains, stderr)
        if params is not None:
            last_params = copy.copy(self.last_params)
            if ignore_params is not None:
                for key in ignore_params:
                    try:
                        del last_params[key]
                    except KeyError:
                        pass
            self.assertDictEqual(params, last_params)
        return stdout, stderr, rc

    def before_parameter_build(self, params, operation, **kwargs):
        self.last_kwargs = params
        self.operations_called.append((operation, params))

    def run_cmd(self, cmd, expected_rc=0):
        logging.debug("Calling cmd: %s", cmd)
        self.patch_make_request()
        self.driver.session.register('before-call', self.before_call)
        self.driver.session.register('before-parameter-build',
                                self.before_parameter_build)
        if not isinstance(cmd, list):
            cmdlist = cmd.split()
        else:
            cmdlist = cmd

        captured_stderr = six.StringIO()
        captured_stdout = six.StringIO()
        with mock.patch('sys.stderr', captured_stderr):
            with mock.patch('sys.stdout', captured_stdout):
                rc = self.driver.main(cmdlist)
        stderr = captured_stderr.getvalue()
        stdout = captured_stdout.getvalue()
        self.assertEqual(
            rc, expected_rc,
            "Unexpected rc (expected: %s, actual: %s) for command: %s" % (
                expected_rc, rc, cmd))
        return stdout, stderr, rc


class FileCreator(object):
    def __init__(self):
        self.rootdir = tempfile.mkdtemp()

    def remove_all(self):
        shutil.rmtree(self.rootdir)

    def create_file(self, filename, contents):
        """Creates a file in a tmpdir

        ``filename`` should be a relative path, e.g. "foo/bar/baz.txt"
        It will be translated into a full path in a tmp dir.

        Returns the full path to the file.
        """
        full_path = os.path.join(self.rootdir, filename)
        if not os.path.isdir(os.path.dirname(full_path)):
            os.makedirs(os.path.dirname(full_path))
        with open(full_path, 'w') as f:
            f.write(contents)
        return full_path

    def full_path(self, filename):
        """Translate relative path to full path in temp dir.

        f.full_path('foo/bar.txt') -> /tmp/asdfasd/foo/bar.txt
        """
        return os.path.join(self.rootdir, filename)
