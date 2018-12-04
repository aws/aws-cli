# Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import tempfile
import shutil

from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.testutils import unittest, skip_if_windows


class TestConfigFileWriter(unittest.TestCase):

    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.config_filename = os.path.join(self.dirname, 'config')
        self.writer = ConfigFileWriter()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def assert_update_config(self, original_config_contents, updated_data,
                             updated_config_contents):
        # Given the original_config, when it's updated with update_data,
        # it should produce updated_config_contents.
        with open(self.config_filename, 'w') as f:
            f.write(original_config_contents)
        self.writer.update_config(updated_data, self.config_filename)
        with open(self.config_filename, 'r') as f:
            new_contents = f.read()
        if new_contents != updated_config_contents:
            self.fail("Config file contents do not match.\n"
                      "Expected contents:\n"
                      "%s\n\n"
                      "Actual Contents:\n"
                      "%s\n" % (updated_config_contents, new_contents))

    def test_update_single_existing_value(self):
        original = '[default]\nfoo = 1\nbar = 1'
        updated = '[default]\nfoo = newvalue\nbar = 1'
        self.assert_update_config(
            original, {'foo': 'newvalue'}, updated)

    def test_update_single_existing_value_no_spaces(self):
        original = '[default]\nfoo=1\nbar=1'
        updated = '[default]\nfoo = newvalue\nbar=1'
        self.assert_update_config(
            original, {'foo': 'newvalue'}, updated)

    def test_update_single_new_values(self):
        expected = '[default]\nfoo = 1\nbar = 2\nbaz = newvalue\n'
        self.assert_update_config(
            '[default]\nfoo = 1\nbar = 2',
            {'baz': 'newvalue'}, expected)

    def test_handles_no_spaces(self):
        expected = '[default]\nfoo=1\nbar=2\nbaz = newvalue\n'
        self.assert_update_config(
            '[default]\nfoo=1\nbar=2',
            {'baz': 'newvalue'}, expected)

    def test_insert_values_in_middle_section(self):
        original_contents = (
            '[a]\n'
            'foo = bar\n'
            'baz = bar\n'
            '\n'
            '[b]\n'
            '\n'
            'foo = bar\n'
            '[c]\n'
            'foo = bar\n'
            'baz = bar\n'
        )
        expected_contents = (
            '[a]\n'
            'foo = bar\n'
            'baz = bar\n'
            '\n'
            '[b]\n'
            '\n'
            'foo = newvalue\n'
            '[c]\n'
            'foo = bar\n'
            'baz = bar\n'
        )
        self.assert_update_config(
            original_contents,
            {'foo': 'newvalue', '__section__': 'b'},
            expected_contents)

    def test_insert_new_value_in_middle_section(self):
        original_contents = (
            '[a]\n'
            'foo = bar\n'
            '\n'
            '[b]\n'
            '\n'
            'foo = bar\n'
            '\n'
            '[c]\n'
            'foo = bar\n'
        )
        expected_contents = (
            '[a]\n'
            'foo = bar\n'
            '\n'
            '[b]\n'
            '\n'
            'foo = bar\n'
            'newvalue = newvalue\n'
            '\n'
            '[c]\n'
            'foo = bar\n'
        )
        self.assert_update_config(
            original_contents,
            {'newvalue': 'newvalue', '__section__': 'b'},
            expected_contents)

    def test_new_config_file(self):
        self.assert_update_config(
            '\n',
            {'foo': 'value'},
            '\n[default]\nfoo = value\n')

    def test_section_does_not_exist(self):
        original_contents = (
            '[notdefault]\n'
            'foo = bar\n'
            'baz = bar\n'
            '\n'
            '\n'
            '\n'
            '[other "section"]\n'
            '\n'
            'foo = bar\n'
        )
        appended_contents = (
            '[default]\n'
            'foo = value\n'
        )
        self.assert_update_config(
            original_contents,
            {'foo': 'value'},
            original_contents + appended_contents)

    def test_config_file_does_not_exist(self):
        self.writer.update_config({'foo': 'value'}, self.config_filename)
        with open(self.config_filename, 'r') as f:
            new_contents = f.read()
        self.assertEqual(new_contents, '[default]\nfoo = value\n')

    @skip_if_windows("Test not valid on windows.")
    def test_permissions_on_new_file(self):
        self.writer.update_config({'foo': 'value'}, self.config_filename)
        with open(self.config_filename, 'r') as f:
            f.read()
        self.assertEqual(os.stat(self.config_filename).st_mode & 0xFFF, 0o600)

    def test_update_config_with_comments(self):
        original = (
            '[default]\n'
            '#foo = 1\n'
            'bar = 1\n'
        )
        self.assert_update_config(
            original, {'foo': 'newvalue'},
            '[default]\n'
            '#foo = 1\n'
            'bar = 1\n'
            'foo = newvalue\n'
        )

    def test_update_config_with_commented_section(self):
        original = (
            '#[default]\n'
            '[default]\n'
            '#foo = 1\n'
            'bar = 1\n'
        )
        self.assert_update_config(
            original, {'foo': 'newvalue'},
            '#[default]\n'
            '[default]\n'
            '#foo = 1\n'
            'bar = 1\n'
            'foo = newvalue\n'
        )

    def test_spaces_around_key_names(self):
        original = (
            '[default]\n'
            'foo = 1\n'
            'bar = 1\n'
        )
        self.assert_update_config(
            original, {'foo': 'newvalue'},
            '[default]\n'
            'foo = newvalue\n'
            'bar = 1\n'
        )

    def test_unquoted_profile_name(self):
        original = (
            '[profile foobar]\n'
            'foo = 1\n'
            'bar = 1\n'
        )
        self.assert_update_config(
            original, {'foo': 'newvalue', '__section__': 'profile foobar'},
            '[profile foobar]\n'
            'foo = newvalue\n'
            'bar = 1\n'
        )

    def test_double_quoted_profile_name(self):
        original = (
            '[profile "foobar"]\n'
            'foo = 1\n'
            'bar = 1\n'
        )
        self.assert_update_config(
            original, {'foo': 'newvalue', '__section__': 'profile foobar'},
            '[profile "foobar"]\n'
            'foo = newvalue\n'
            'bar = 1\n'
        )

    def test_profile_with_multiple_spaces(self):
        original = (
            '[profile "two  spaces"]\n'
            'foo = 1\n'
            'bar = 1\n'
        )
        self.assert_update_config(
            original, {
                'foo': 'newvalue', '__section__': 'profile two  spaces'},
            '[profile "two  spaces"]\n'
            'foo = newvalue\n'
            'bar = 1\n'
        )

    def test_nested_attributes_new_file(self):
        original = ''
        self.assert_update_config(
            original, {'__section__': 'default',
                       's3': {'signature_version': 's3v4'}},
            '[default]\n'
            's3 =\n'
            '    signature_version = s3v4\n')

    def test_add_to_nested_with_nested_in_the_middle(self):
        original = (
            '[default]\n'
            's3 =\n'
            '    other = foo\n'
            'ec2 = bar\n'
        )
        self.assert_update_config(
            original, {'__section__': 'default',
                       's3': {'signature_version': 'newval'}},
            '[default]\n'
            's3 =\n'
            '    other = foo\n'
            '    signature_version = newval\n'
            'ec2 = bar\n')

    def test_add_to_nested_with_nested_in_the_end(self):
        original = (
            '[default]\n'
            's3 =\n'
            '    other = foo\n'
        )
        self.assert_update_config(
            original, {'__section__': 'default',
                       's3': {'signature_version': 'newval'}},
            '[default]\n'
            's3 =\n'
            '    other = foo\n'
            '    signature_version = newval\n')

    def test_update_nested_attribute(self):
        original = (
            '[default]\n'
            's3 =\n'
            '    signature_version = originalval\n'
        )
        self.assert_update_config(
            original, {'__section__': 'default',
                       's3': {'signature_version': 'newval'}},
            '[default]\n'
            's3 =\n'
            '    signature_version = newval\n')

    def test_updated_nested_attribute_new_section(self):
        original = (
            '[default]\n'
            's3 =\n'
            '    other = foo\n'
            '[profile foo]\n'
            'foo = bar\n'
        )
        self.assert_update_config(
            original, {'__section__': 'default',
                       's3': {'signature_version': 'newval'}},
            '[default]\n'
            's3 =\n'
            '    other = foo\n'
            '    signature_version = newval\n'
            '[profile foo]\n'
            'foo = bar\n')

    def test_update_nested_attr_no_prior_nesting(self):
        original = (
            '[default]\n'
            'foo = bar\n'
            '[profile foo]\n'
            'foo = bar\n'
        )
        self.assert_update_config(
            original, {'__section__': 'default',
                       's3': {'signature_version': 'newval'}},
            '[default]\n'
            'foo = bar\n'
            's3 =\n'
            '    signature_version = newval\n'
            '[profile foo]\n'
            'foo = bar\n')

    def test_can_handle_empty_section(self):
        original = (
            '[default]\n'
            '[preview]\n'
            'cloudfront = true\n'
        )
        self.assert_update_config(
            original, {'region': 'us-west-2', '__section__': 'default'},
            '[default]\n'
            'region = us-west-2\n'
            '[preview]\n'
            'cloudfront = true\n'
        )
