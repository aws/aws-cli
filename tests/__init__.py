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
import os
import sys
import contextlib
import shutil
import tempfile
import time
import random

import mock
from botocore.hooks import HierarchicalEmitter
from botocore.session import Session

import awscli.clidriver
from awscli.plugin import load_plugins
from awscli.clidriver import CLIDriver
from awscli import EnvironmentVariables
import botocore.loaders


# The unittest module got a significant overhaul
# in 2.7, so if we're in 2.6 we can use the backported
# version unittest2.
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest


_LOADER = botocore.loaders.Loader()


def create_clidriver():
    driver = awscli.clidriver.create_clidriver()
    driver.session._loader = _LOADER
    return driver


class BaseCLIDriverTest(unittest.TestCase):
    """Base unittest that use clidriver.

    This will load all the default plugins as well so it
    will simulate the behavior the user will see.
    """
    def setUp(self):
        self.environ = {
            'AWS_DATA_PATH': os.environ['AWS_DATA_PATH'],
            'AWS_DEFAULT_REGION': 'us-east-1',
            'AWS_ACCESS_KEY_ID': 'access_key',
            'AWS_SECRET_ACCESS_KEY': 'secret_key',
            'AWS_CONFIG_FILE': '',
        }
        self.environ_patch = mock.patch('os.environ', self.environ)
        self.environ_patch.start()
        emitter = HierarchicalEmitter()
        session = Session(EnvironmentVariables, emitter, loader=_LOADER)
        load_plugins({}, event_hooks=emitter)
        driver = CLIDriver(session=session)
        self.session = session
        self.driver = driver

    def tearDown(self):
        self.environ_patch.stop()


class BaseAWSHelpOutputTest(BaseCLIDriverTest):
    def setUp(self):
        super(BaseAWSHelpOutputTest, self).setUp()
        self.renderer_patch = mock.patch('awscli.help.get_renderer')
        self.renderer_mock = self.renderer_patch.start()
        self.renderer = CapturedRenderer()
        self.renderer_mock.return_value = self.renderer

    def tearDown(self):
        super(BaseAWSHelpOutputTest, self).tearDown()
        self.renderer_patch.stop()

    def assert_contains(self, contains):
        if contains not in self.renderer.rendered_contents:
            self.fail("The expected contents:\n%s\nwere not in the "
                      "actual rendered contents:\n%s" % (
                          contains, self.renderer.rendered_contents))

    def assert_not_contains(self, contents):
        if contents in self.renderer.rendered_contents:
            self.fail("The contents:\n%s\nwere not suppose to be in the "
                      "actual rendered contents:\n%s" % (
                          contents, self.renderer.rendered_contents))

    def assert_text_order(self, *args, **kwargs):
        # First we need to find where the SYNOPSIS section starts.
        starting_from = kwargs.pop('starting_from')
        args = list(args)
        contents = self.renderer.rendered_contents
        self.assertIn(starting_from, contents)
        start_index = contents.find(starting_from)
        arg_indices = [contents.find(arg, start_index) for arg in args]
        previous = arg_indices[0]
        for i, index in enumerate(arg_indices[1:], 1):
            if index == -1:
                self.fail('The string %r was not found in the contents: %s'
                          % (args[index], contents))
            if index < previous:
                self.fail('The string %r came before %r, but was suppose to come '
                          'after it.\n%s' % (args[i], args[i - 1], contents))
            previous = index


class CapturedRenderer(object):
    def __init__(self):
        self.rendered_contents = ''

    def render(self, contents):
        self.rendered_contents = contents.decode('utf-8')


@contextlib.contextmanager
def temporary_file(mode):
    """This is a cross platform temporary file creation.

    tempfile.NamedTemporary file on windows creates a secure temp file
    that can't be read by other processes and can't be opened a second time.

    For tests, we generally *want* them to be read multiple times.
    The test fixture writes the temp file contents, the test reads the
    temp file.

    """
    temporary_directory = tempfile.mkdtemp()
    basename = 'tmpfile-%s-%s' % (int(time.time()), random.randint(1, 1000))
    full_filename = os.path.join(temporary_directory, basename)
    open(full_filename, 'w').close()
    try:
        with open(full_filename, mode) as f:
            yield f
    finally:
        shutil.rmtree(temporary_directory)
