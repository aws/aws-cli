#!/usr/bin/env
# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
from tests import unittest, BaseEnvVar
import os
import botocore.session
import botocore.exceptions


def path(filename):
    return os.path.join(os.path.dirname(__file__), 'cfg', filename)


class TestConfig(BaseEnvVar):

    def setUp(self):
        super(TestConfig, self).setUp()
        self.env_vars = {
            'config_file': (None, 'FOO_CONFIG_FILE', None),
            'profile': (None, 'FOO_DEFAULT_PROFILE', None),
        }

    def test_config_not_found(self):
        self.environ['FOO_CONFIG_FILE'] = path('aws_config_notfound')
        session = botocore.session.get_session(self.env_vars)
        self.assertEqual(session.get_config(), {})

    def test_config_parse_error(self):
        self.environ['FOO_CONFIG_FILE'] = path('aws_config_bad')
        session = botocore.session.get_session(self.env_vars)
        self.assertRaises(botocore.exceptions.ConfigParseError,
                          session.get_config)

    def test_config(self):
        self.environ['FOO_CONFIG_FILE'] = path('aws_config')
        session = botocore.session.get_session(self.env_vars)
        session.get_config()
        self.assertEqual(len(session.available_profiles), 2)
        self.assertIn('default', session.available_profiles)
        self.assertIn('personal', session.available_profiles)

    def test_default_values_are_used_in_configs(self):
        env_vars = {'config_file': (
            None, 'FOO_CONFIG_FILE', path('aws_config'))}
        session = botocore.session.get_session(env_vars)
        config = session.get_config()
        self.assertEqual(config['aws_access_key_id'], 'foo')
        self.assertEqual(config['aws_secret_access_key'], 'bar')

    def test_env_vars_trump_defaults(self):
        env_vars = {'config_file': (
            None, 'FOO_CONFIG_FILE', path('aws_config'))}
        self.environ['FOO_CONFIG_FILE'] = path('aws_config_other')
        # aws_config has access/secret keys of foo/bar, while
        # aws_config_other has access/secret key of other_foo/other_bar,
        # which is what should be used by the session since env vars
        # trump the default value.
        session = botocore.session.get_session(env_vars)
        config = session.get_config()
        self.assertEqual(config['aws_access_key_id'], 'other_foo')
        self.assertEqual(config['aws_secret_access_key'], 'other_bar')

    def test_bad_profile(self):
        self.environ['FOO_CONFIG_FILE'] = path('aws_bad_profile')
        self.environ['FOO_DEFAULT_PROFILE'] = 'personal1'
        session = botocore.session.get_session(self.env_vars)
        config = session.get_config()
        profiles = session.available_profiles
        self.assertEqual(len(profiles), 3)
        self.assertIn('my profile', profiles)
        self.assertIn('personal1', profiles)
        self.assertIn('default', profiles)
        self.assertEqual(config, {'aws_access_key_id': 'access_personal1',
                                  'aws_secret_access_key': 'key_personal1'})

    def test_profile_cached_returns_same_values(self):
        self.environ['FOO_CONFIG_FILE'] = path('aws_bad_profile')
        self.environ['FOO_DEFAULT_PROFILE'] = 'personal1'
        session = botocore.session.get_session(self.env_vars)
        # First time is built from scratch.
        config = session.get_config()
        # Second time is cached.
        cached_config = session.get_config()
        # Both versions should be identical.
        self.assertEqual(config, cached_config)


if __name__ == "__main__":
    unittest.main()
