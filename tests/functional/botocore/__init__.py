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
import uuid

import botocore
from tests import BaseEnvVar

_ORIGINAL = os.environ.copy()
# These are environment variables that allow users to control
# the location of config files used by botocore.
_CONFIG_FILE_ENV_VARS = [
    'AWS_CONFIG_FILE',
    'AWS_SHARED_CREDENTIALS_FILE',
    'BOTO_CONFIG',
]
_CREDENTIAL_ENV_VARS = [
    'AWS_ACCESS_KEY_ID',
    'AWS_SECRET_ACCESS_KEY',
    'AWS_SESSION_TOKEN',
]

TEST_MODELS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'models',
)


def create_session(**kwargs):
    # Create session and inject functional test models into loader
    loader = _create_functional_test_loader()
    session = botocore.session.Session(**kwargs)
    session.register_component('data_loader', loader)
    session.set_config_variable('credentials_file', 'noexist/foo/botocore')
    return session


def _create_functional_test_loader():
    loader = botocore.loaders.Loader()
    loader.search_paths.insert(0, TEST_MODELS_DIR)
    return loader


class FunctionalSessionTest(BaseEnvVar):
    def setUp(self, **environ):
        super().setUp()
        self.environ['AWS_ACCESS_KEY_ID'] = 'access_key'
        self.environ['AWS_SECRET_ACCESS_KEY'] = 'secret_key'
        self.environ['AWS_CONFIG_FILE'] = 'no-exist-foo'
        self.environ.update(environ)
        self.session = create_session()
        self.session.config_filename = 'no-exist-foo'


def setup_package():
    # We're using a random uuid to ensure we're pointing
    # AWS_CONFIG_FILE and other env vars at a filename that
    # does not exist.
    random_file = str(uuid.uuid4())
    for varname in _CONFIG_FILE_ENV_VARS:
        # The reason we're doing this is to ensure we don't automatically pick
        # up any credentials a developer might have configured on their local
        # machine.  Travis will not have any credentials available, so without
        # this fixture setup, it's possible to have all the tests pass on your
        # local machine (if you have credentials configured) but still fail on
        # travis.
        os.environ[varname] = random_file
    for credvar in _CREDENTIAL_ENV_VARS:
        os.environ.pop(credvar, None)


def teardown_package():
    os.environ = _ORIGINAL
