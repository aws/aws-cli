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
import unittest
import os
import botocore.session
import botocore.exceptions


class TestConfig(unittest.TestCase):

    def setUp(self):
        self.env_vars = {'config_file': (None, 'FOO_CONFIG_FILE')}

    def test_config_not_found(self):
        config_path = os.path.join(os.path.dirname(__file__),
                                   'aws_config_notfound')
        os.environ['FOO_CONFIG_FILE'] = config_path
        session = botocore.session.get_session(self.env_vars)
        self.assertRaises(botocore.exceptions.ConfigNotFound,
                          session.get_config)

    def test_config_parse_error(self):
        config_path = os.path.join(os.path.dirname(__file__),
                                   'aws_config_bad')
        os.environ['FOO_CONFIG_FILE'] = config_path
        session = botocore.session.get_session(self.env_vars)
        self.assertRaises(botocore.exceptions.ConfigParseError,
                          session.get_config)

    def test_config(self):
        config_path = os.path.join(os.path.dirname(__file__),
                                   'aws_config')
        os.environ['FOO_CONFIG_FILE'] = config_path
        session = botocore.session.get_session(self.env_vars)
        session.get_config()
        assert len(session.available_profiles) == 2
        assert 'default' in session.available_profiles
        assert 'personal' in session.available_profiles

    def tearDown(self):
        del os.environ['FOO_CONFIG_FILE']


if __name__ == "__main__":
    unittest.main()
