#!/usr/bin/env
# Copyright (c) 2012-2013 Mitch Garnaat http://garnaat.org/
# Copyright 2012-2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import shutil
import tempfile

import botocore.exceptions
from botocore.configloader import (
    load_config,
    multi_file_load_config,
    raw_config_parse,
)

from tests import BaseEnvVar, mock, unittest


def path(filename):
    directory = os.path.join(os.path.dirname(__file__), 'cfg')
    if isinstance(filename, bytes):
        directory = directory.encode('latin-1')
    return os.path.join(directory, filename)


class TestConfigLoader(BaseEnvVar):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def create_config_file(self, filename):
        contents = (
            '[default]\n'
            'aws_access_key_id = foo\n'
            'aws_secret_access_key = bar\n\n'
            '[profile "personal"]\n'
            'aws_access_key_id = fie\n'
            'aws_secret_access_key = baz\n'
            'aws_security_token = fiebaz\n'
        )

        directory = self.tempdir
        if isinstance(filename, bytes):
            directory = directory.encode('latin-1')
        full_path = os.path.join(directory, filename)

        with open(full_path, 'w') as f:
            f.write(contents)
        return full_path

    def test_config_not_found(self):
        with self.assertRaises(botocore.exceptions.ConfigNotFound):
            raw_config_parse(path('aws_config_notfound'))

    def test_config_parse_error(self):
        filename = path('aws_config_bad')
        with self.assertRaises(botocore.exceptions.ConfigParseError):
            raw_config_parse(filename)

    def test_config_parse_error_bad_unicode(self):
        filename = path('aws_config_badbytes')
        with self.assertRaises(botocore.exceptions.ConfigParseError):
            raw_config_parse(filename)

    def test_config_parse_error_filesystem_encoding_none(self):
        filename = path('aws_config_bad')
        with mock.patch('sys.getfilesystemencoding') as encoding:
            encoding.return_value = None
            with self.assertRaises(botocore.exceptions.ConfigParseError):
                raw_config_parse(filename)

    def test_config(self):
        loaded_config = raw_config_parse(path('aws_config'))
        self.assertIn('default', loaded_config)
        self.assertIn('profile "personal"', loaded_config)

    def test_profile_map_conversion(self):
        loaded_config = load_config(path('aws_config'))
        self.assertIn('profiles', loaded_config)
        self.assertEqual(
            sorted(loaded_config['profiles'].keys()), ['default', 'personal']
        )

    def test_bad_profiles_are_ignored(self):
        filename = path('aws_bad_profile')
        loaded_config = load_config(filename)
        self.assertEqual(len(loaded_config['profiles']), 3)
        profiles = loaded_config['profiles']
        self.assertIn('my profile', profiles)
        self.assertIn('personal1', profiles)
        self.assertIn('default', profiles)

    def test_nested_hierarchy_parsing(self):
        filename = path('aws_config_nested')
        loaded_config = load_config(filename)
        config = loaded_config['profiles']['default']
        self.assertEqual(config['aws_access_key_id'], 'foo')
        self.assertEqual(config['region'], 'us-west-2')
        self.assertEqual(config['s3']['signature_version'], 's3v4')
        self.assertEqual(config['cloudwatch']['signature_version'], 'v4')

    def test_nested_hierarchy_with_no_subsection_parsing(self):
        filename = path('aws_config_nested')
        raw_config = raw_config_parse(filename, False)['default']
        self.assertEqual(raw_config['aws_access_key_id'], 'foo')
        self.assertEqual(raw_config['region'], 'us-west-2')
        # Specifying False for pase_subsections in raw_config_parse
        # will make sure that indented sections such as singature_version
        # will not be treated as another subsection but rather
        # its literal value.
        self.assertEqual(raw_config['cloudwatch'], '\nsignature_version = v4')
        self.assertEqual(
            raw_config['s3'],
            '\nsignature_version = s3v4' '\naddressing_style = path',
        )

    def test_nested_bad_config(self):
        filename = path('aws_config_nested_bad')
        with self.assertRaises(botocore.exceptions.ConfigParseError):
            load_config(filename)

    def test_nested_bad_config_filesystem_encoding_none(self):
        filename = path('aws_config_nested_bad')
        with mock.patch('sys.getfilesystemencoding') as encoding:
            encoding.return_value = None
            with self.assertRaises(botocore.exceptions.ConfigParseError):
                load_config(filename)

    def test_multi_file_load(self):
        filenames = [
            path('aws_config_other'),
            path('aws_config'),
            path('aws_third_config'),
            path('aws_config_notfound'),
        ]
        loaded_config = multi_file_load_config(*filenames)
        config = loaded_config['profiles']['default']
        self.assertEqual(config['aws_access_key_id'], 'other_foo')
        self.assertEqual(config['aws_secret_access_key'], 'other_bar')
        second_config = loaded_config['profiles']['personal']
        self.assertEqual(second_config['aws_access_key_id'], 'fie')
        self.assertEqual(second_config['aws_secret_access_key'], 'baz')
        self.assertEqual(second_config['aws_security_token'], 'fiebaz')
        third_config = loaded_config['profiles']['third']
        self.assertEqual(third_config['aws_access_key_id'], 'third_fie')
        self.assertEqual(third_config['aws_secret_access_key'], 'third_baz')
        self.assertEqual(third_config['aws_security_token'], 'third_fiebaz')

    def test_unicode_bytes_path_not_found(self):
        with self.assertRaises(botocore.exceptions.ConfigNotFound):
            with mock.patch('sys.getfilesystemencoding') as encoding:
                encoding.return_value = 'utf-8'
                load_config(path(b'\xe2\x9c\x93'))

    def test_unicode_bytes_path_not_found_filesystem_encoding_none(self):
        with mock.patch('sys.getfilesystemencoding') as encoding:
            encoding.return_value = None
            with self.assertRaises(botocore.exceptions.ConfigNotFound):
                load_config(path(b'\xe2\x9c\x93'))

    def test_unicode_bytes_path(self):
        filename = self.create_config_file(b'aws_config_unicode\xe2\x9c\x93')
        with mock.patch('sys.getfilesystemencoding') as encoding:
            encoding.return_value = 'utf-8'
            loaded_config = load_config(filename)
        self.assertIn('default', loaded_config['profiles'])
        self.assertIn('personal', loaded_config['profiles'])

    def test_sso_session_config(self):
        filename = path('aws_sso_session_config')
        loaded_config = load_config(filename)
        self.assertIn('profiles', loaded_config)
        self.assertIn('default', loaded_config['profiles'])
        self.assertIn('sso_sessions', loaded_config)
        self.assertIn('sso', loaded_config['sso_sessions'])
        sso_config = loaded_config['sso_sessions']['sso']
        self.assertEqual(sso_config['sso_region'], 'us-east-1')
        self.assertEqual(sso_config['sso_start_url'], 'https://example.com')

    def test_services_config(self):
        filename = path('aws_services_config')
        loaded_config = load_config(filename)
        self.assertIn('profiles', loaded_config)
        self.assertIn('default', loaded_config['profiles'])
        self.assertIn('services', loaded_config)
        self.assertIn('my-services', loaded_config['services'])
        services_config = loaded_config['services']['my-services']
        self.assertIn('s3', services_config)
        self.assertIn('dynamodb', services_config)
        self.assertEqual(
            services_config['s3']['endpoint_url'], 'https://localhost:5678/'
        )
        self.assertEqual(
            services_config['dynamodb']['endpoint_url'],
            'https://localhost:8888/',
        )

    def test_duplicate_profile_error_message(self):
        contents = (
            '[default]\n'
            'region = us-west-2\n\n'
            '[profile xyz]\n'
            'aws_access_key_id = foo\n'
            'aws_secret_access_key = bar\n\n'
            '[profile other]\n'
            'region = eu-west-1\n\n'
            '[profile xyz]\n'
            'aws_access_key_id = baz\n'
        )
        full_path = os.path.join(self.tempdir, 'aws_config_dup_profile')
        with open(full_path, 'w') as f:
            f.write(contents)

        with self.assertRaises(botocore.exceptions.ConfigParseError) as cm:
            raw_config_parse(full_path)
        expected_msg = (
            f"Unable to parse config file: {full_path} - "
            "Found duplicate profile 'xyz' "
            "(first seen on line 4, duplicated on line 11)"
        )
        self.assertEqual(str(cm.exception), expected_msg)

        # Also verify load_config raises the same error
        with self.assertRaises(botocore.exceptions.ConfigParseError) as cm:
            load_config(full_path)
        self.assertEqual(str(cm.exception), expected_msg)

    def test_duplicate_profile_with_quotes_error_message(self):
        contents = (
            '[profile "personal"]\n'
            'aws_access_key_id = foo\n'
            'aws_secret_access_key = bar\n\n'
            '[profile "personal"]\n'
            'aws_access_key_id = baz\n'
        )
        full_path = os.path.join(self.tempdir, 'aws_config_dup_quotes')
        with open(full_path, 'w') as f:
            f.write(contents)

        with self.assertRaises(botocore.exceptions.ConfigParseError) as cm:
            raw_config_parse(full_path)
        expected_msg = (
            f"Unable to parse config file: {full_path} - "
            "Found duplicate profile 'personal' "
            "(first seen on line 1, duplicated on line 5)"
        )
        self.assertEqual(str(cm.exception), expected_msg)

    def test_duplicate_default_profile_error_message(self):
        contents = (
            '[default]\n'
            'region = us-west-2\n\n'
            '[default]\n'
            'region = us-east-1\n'
        )
        full_path = os.path.join(self.tempdir, 'aws_config_dup_default')
        with open(full_path, 'w') as f:
            f.write(contents)

        with self.assertRaises(botocore.exceptions.ConfigParseError) as cm:
            raw_config_parse(full_path)
        expected_msg = (
            f"Unable to parse config file: {full_path} - "
            "Found duplicate profile 'default' "
            "(first seen on line 1, duplicated on line 4)"
        )
        self.assertEqual(str(cm.exception), expected_msg)

    def test_duplicate_section_error_message(self):
        contents = (
            '[sso-session my-session]\n'
            'sso_region = us-west-2\n\n'
            '[sso-session my-session]\n'
            'sso_region = us-east-1\n'
        )
        full_path = os.path.join(self.tempdir, 'aws_config_dup_section')
        with open(full_path, 'w') as f:
            f.write(contents)

        with self.assertRaises(botocore.exceptions.ConfigParseError) as cm:
            raw_config_parse(full_path)
        expected_msg = (
            f"Unable to parse config file: {full_path} - "
            "Found duplicate section 'sso-session my-session' "
            "(first seen on line 1, duplicated on line 4)"
        )
        self.assertEqual(str(cm.exception), expected_msg)


if __name__ == "__main__":
    unittest.main()
