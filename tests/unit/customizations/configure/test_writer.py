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
import shutil
import tempfile

from awscli.customizations.configure.writer import ConfigFileWriter
from awscli.testutils import mock, skip_if_windows, unittest


class TestConfigFileWriter(unittest.TestCase):
    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.config_filename = os.path.join(self.dirname, 'config')
        self.writer = ConfigFileWriter()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def assert_update_config(
        self, original_config_contents, updated_data, updated_config_contents
    ):
        # Given the original_config, when it's updated with update_data,
        # it should produce updated_config_contents.
        with open(self.config_filename, 'w') as f:
            f.write(original_config_contents)
        self.writer.update_config(updated_data, self.config_filename)
        with open(self.config_filename) as f:
            new_contents = f.read()
        if new_contents != updated_config_contents:
            self.fail(
                "Config file contents do not match.\n"
                "Expected contents:\n"
                "%s\n\n"
                "Actual Contents:\n"
                "%s\n" % (updated_config_contents, new_contents)
            )

    def test_update_single_existing_value(self):
        original = '[default]\nfoo = 1\nbar = 1'
        updated = '[default]\nfoo = newvalue\nbar = 1'
        self.assert_update_config(original, {'foo': 'newvalue'}, updated)

    def test_update_value_with_square_brackets(self):
        original = '[default]\nfoo = old[value]\nbar = 1'
        updated = '[default]\nfoo = new[value]\nbar = 1'
        self.assert_update_config(original, {'foo': 'new[value]'}, updated)

    def test_update_single_existing_value_no_spaces(self):
        original = '[default]\nfoo=1\nbar=1'
        updated = '[default]\nfoo = newvalue\nbar=1'
        self.assert_update_config(original, {'foo': 'newvalue'}, updated)

    def test_update_single_new_values(self):
        expected = '[default]\nfoo = 1\nbar = 2\nbaz = newvalue\n'
        self.assert_update_config(
            '[default]\nfoo = 1\nbar = 2', {'baz': 'newvalue'}, expected
        )

    def test_handles_no_spaces(self):
        expected = '[default]\nfoo=1\nbar=2\nbaz = newvalue\n'
        self.assert_update_config(
            '[default]\nfoo=1\nbar=2', {'baz': 'newvalue'}, expected
        )

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
            expected_contents,
        )

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
            expected_contents,
        )

    def test_new_config_file(self):
        self.assert_update_config(
            '\n', {'foo': 'value'}, '\n[default]\nfoo = value\n'
        )

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
        appended_contents = '[default]\n' 'foo = value\n'
        self.assert_update_config(
            original_contents,
            {'foo': 'value'},
            original_contents + appended_contents,
        )

    def test_config_file_does_not_exist(self):
        self.writer.update_config({'foo': 'value'}, self.config_filename)
        with open(self.config_filename) as f:
            new_contents = f.read()
        self.assertEqual(new_contents, '[default]\nfoo = value\n')

    @skip_if_windows("Test not valid on windows.")
    def test_permissions_on_new_file(self):
        self.writer.update_config({'foo': 'value'}, self.config_filename)
        with open(self.config_filename) as f:
            f.read()
        self.assertEqual(os.stat(self.config_filename).st_mode & 0xFFF, 0o600)

    def test_update_config_with_comments(self):
        original = '[default]\n' '#foo = 1\n' 'bar = 1\n'
        self.assert_update_config(
            original,
            {'foo': 'newvalue'},
            '[default]\n' '#foo = 1\n' 'bar = 1\n' 'foo = newvalue\n',
        )

    def test_update_config_with_commented_section(self):
        original = '#[default]\n' '[default]\n' '#foo = 1\n' 'bar = 1\n'
        self.assert_update_config(
            original,
            {'foo': 'newvalue'},
            '#[default]\n'
            '[default]\n'
            '#foo = 1\n'
            'bar = 1\n'
            'foo = newvalue\n',
        )

    def test_spaces_around_key_names(self):
        original = '[default]\n' 'foo = 1\n' 'bar = 1\n'
        self.assert_update_config(
            original,
            {'foo': 'newvalue'},
            '[default]\n' 'foo = newvalue\n' 'bar = 1\n',
        )

    def test_unquoted_profile_name(self):
        original = '[profile foobar]\n' 'foo = 1\n' 'bar = 1\n'
        self.assert_update_config(
            original,
            {'foo': 'newvalue', '__section__': 'profile foobar'},
            '[profile foobar]\n' 'foo = newvalue\n' 'bar = 1\n',
        )

    def test_double_quoted_profile_name(self):
        original = '[profile "foobar"]\n' 'foo = 1\n' 'bar = 1\n'
        self.assert_update_config(
            original,
            {'foo': 'newvalue', '__section__': 'profile foobar'},
            '[profile "foobar"]\n' 'foo = newvalue\n' 'bar = 1\n',
        )

    def test_profile_with_multiple_spaces(self):
        original = '[profile "two  spaces"]\n' 'foo = 1\n' 'bar = 1\n'
        self.assert_update_config(
            original,
            {'foo': 'newvalue', '__section__': 'profile two  spaces'},
            '[profile "two  spaces"]\n' 'foo = newvalue\n' 'bar = 1\n',
        )

    def test_nested_attributes_new_file(self):
        original = ''
        self.assert_update_config(
            original,
            {'__section__': 'default', 's3': {'signature_version': 's3v4'}},
            '[default]\n' 's3 =\n' '    signature_version = s3v4\n',
        )

    def test_add_to_nested_with_nested_in_the_middle(self):
        original = '[default]\n' 's3 =\n' '    other = foo\n' 'ec2 = bar\n'
        self.assert_update_config(
            original,
            {'__section__': 'default', 's3': {'signature_version': 'newval'}},
            '[default]\n'
            's3 =\n'
            '    other = foo\n'
            '    signature_version = newval\n'
            'ec2 = bar\n',
        )

    def test_add_to_nested_with_nested_in_the_end(self):
        original = '[default]\n' 's3 =\n' '    other = foo\n'
        self.assert_update_config(
            original,
            {'__section__': 'default', 's3': {'signature_version': 'newval'}},
            '[default]\n'
            's3 =\n'
            '    other = foo\n'
            '    signature_version = newval\n',
        )

    def test_update_nested_attribute(self):
        original = (
            '[default]\n' 's3 =\n' '    signature_version = originalval\n'
        )
        self.assert_update_config(
            original,
            {'__section__': 'default', 's3': {'signature_version': 'newval'}},
            '[default]\n' 's3 =\n' '    signature_version = newval\n',
        )

    def test_updated_nested_attribute_new_section(self):
        original = (
            '[default]\n'
            's3 =\n'
            '    other = foo\n'
            '[profile foo]\n'
            'foo = bar\n'
        )
        self.assert_update_config(
            original,
            {'__section__': 'default', 's3': {'signature_version': 'newval'}},
            '[default]\n'
            's3 =\n'
            '    other = foo\n'
            '    signature_version = newval\n'
            '[profile foo]\n'
            'foo = bar\n',
        )

    def test_update_nested_attr_no_prior_nesting(self):
        original = '[default]\n' 'foo = bar\n' '[profile foo]\n' 'foo = bar\n'
        self.assert_update_config(
            original,
            {'__section__': 'default', 's3': {'signature_version': 'newval'}},
            '[default]\n'
            'foo = bar\n'
            's3 =\n'
            '    signature_version = newval\n'
            '[profile foo]\n'
            'foo = bar\n',
        )

    def test_can_handle_empty_section(self):
        original = '[default]\n'
        self.assert_update_config(
            original,
            {'region': 'us-west-2', '__section__': 'default'},
            '[default]\n' 'region = us-west-2\n',
        )

    def test_appends_newline_on_new_section(self):
        original = '[preview]\n' 'cloudfront = true'
        self.assert_update_config(
            original,
            {'region': 'us-west-2', '__section__': 'new-section'},
            '[preview]\n'
            'cloudfront = true\n'
            '[new-section]\n'
            'region = us-west-2\n',
        )

    def test_newline_in_value_raises(self):
        with open(self.config_filename, 'w') as f:
            f.write('[default]\nfoo = bar\n')
        with self.assertRaises(ValueError):
            self.writer.update_config({'foo': 'bad\nvalue'}, self.config_filename)

    def test_carriage_return_in_value_raises(self):
        with open(self.config_filename, 'w') as f:
            f.write('[default]\nfoo = bar\n')
        with self.assertRaises(ValueError):
            self.writer.update_config({'foo': 'bad\rvalue'}, self.config_filename)

    def test_newline_in_key_raises(self):
        with open(self.config_filename, 'w') as f:
            f.write('[default]\nfoo = bar\n')
        with self.assertRaises(ValueError):
            self.writer.update_config({'bad\nkey': 'value'}, self.config_filename)

    def test_newline_in_section_name_raises(self):
        with open(self.config_filename, 'w') as f:
            f.write('[default]\nfoo = bar\n')
        with self.assertRaises(ValueError):
            self.writer.update_config(
                {'foo': 'value', '__section__': 'bad\nsection'},
                self.config_filename
            )

    def test_newline_in_nested_value_raises(self):
        with open(self.config_filename, 'w') as f:
            f.write('[default]\n')
        with self.assertRaises(ValueError):
            self.writer.update_config(
                {'__section__': 'default', 's3': {'key': 'bad\nvalue'}},
                self.config_filename
            )

    @mock.patch('awscli.customizations.configure.writer.warn_if_permissive')
    def test_check_permissions_calls_warn_if_permissive(self, mock_warn):
        with open(self.config_filename, 'w') as f:
            f.write('[default]\n')
        self.writer.update_config(
            {'__section__': 'default', 'key': 'value'},
            self.config_filename,
            check_permissions=True,
        )
        mock_warn.assert_called_once_with(self.config_filename)

    @mock.patch('awscli.customizations.configure.writer.warn_if_permissive')
    def test_no_check_permissions_by_default(self, mock_warn):
        with open(self.config_filename, 'w') as f:
            f.write('[default]\n')
        self.writer.update_config(
            {'__section__': 'default', 'key': 'value'},
            self.config_filename,
        )
        mock_warn.assert_not_called()


class TestRemoveEmptySection(unittest.TestCase):
    KEYS = {'aws_access_key_id': None, 'aws_secret_access_key': None}

    def setUp(self):
        self.dirname = tempfile.mkdtemp()
        self.filename = os.path.join(self.dirname, 'credentials')
        self.writer = ConfigFileWriter()

    def tearDown(self):
        shutil.rmtree(self.dirname)

    def remove_keys(self, original, section='ci', **kwargs):
        with open(self.filename, 'w') as f:
            f.write(original)
        values = dict(self.KEYS, __section__=section)
        self.writer.update_config(
            values, self.filename, remove_empty_section=True, **kwargs
        )
        with open(self.filename) as f:
            return f.read()

    def test_section_goes_with_its_only_keys(self):
        original = '[ci]\naws_access_key_id = a\naws_secret_access_key = b\n'
        self.assertEqual(self.remove_keys(original), '')

    def test_section_with_other_keys_stays(self):
        original = (
            '[ci]\n'
            'aws_access_key_id = a\n'
            'mfa_serial = arn:aws:iam::123456789012:mfa/ci\n'
            'aws_secret_access_key = b\n'
        )
        self.assertEqual(
            self.remove_keys(original),
            '[ci]\nmfa_serial = arn:aws:iam::123456789012:mfa/ci\n',
        )

    def test_neighbours_and_comments_are_unchanged(self):
        before = '# my keys\n[default]\nregion = us-west-2\n; old ci keys\n\n'
        after = (
            '\n[deploy]  # deploy keys\n'
            '#aws_access_key_id = old\n'
            'aws_access_key_id = c\n'
            'aws_secret_access_key = d\n'
        )
        original = (
            before
            + '[ci]\n# rotated 2024\n'
            + 'aws_access_key_id = a\naws_secret_access_key = b\n'
            + after
        )
        self.assertEqual(
            self.remove_keys(original), before + '# rotated 2024\n' + after
        )

    def test_last_section_without_trailing_newline(self):
        original = '[a]\nx = 1\n[ci]\naws_access_key_id = a'
        values = {'aws_access_key_id': None, '__section__': 'ci'}
        with open(self.filename, 'w') as f:
            f.write(original)
        self.writer.update_config(
            values, self.filename, remove_empty_section=True
        )
        with open(self.filename) as f:
            self.assertEqual(f.read(), '[a]\nx = 1\n')

    def test_comment_after_the_header_stays(self):
        for comment in ('# ci keys', '; ci keys'):
            original = (
                f'[ci]  {comment}\n'
                'aws_access_key_id = a\n'
                'aws_secret_access_key = b\n'
            )
            self.assertEqual(self.remove_keys(original), f'{comment}\n')

    def test_default_section(self):
        original = (
            '[default]\naws_access_key_id = a\naws_secret_access_key = b\n'
            '[ci]\nregion = us-west-2\n'
        )
        self.assertEqual(
            self.remove_keys(original, section='default'),
            '[ci]\nregion = us-west-2\n',
        )

    def test_name_with_a_space(self):
        for header in ('[my ci]', '[my "ci"]'):
            original = (
                f'{header}\n'
                'aws_access_key_id = a\n'
                'aws_secret_access_key = b\n'
                '[deploy]\nregion = us-west-2\n'
            )
            self.assertEqual(
                self.remove_keys(original, section='my ci'),
                '[deploy]\nregion = us-west-2\n',
            )

    def test_last_section_of_comments_and_keys_without_trailing_newline(
        self,
    ):
        original = (
            '[a]\nx = 1\n'
            '[ci]  # ci keys\n# only comments\n; and this\n'
            'aws_access_key_id = a\naws_secret_access_key = b'
        )
        self.assertEqual(
            self.remove_keys(original),
            '[a]\nx = 1\n# ci keys\n# only comments\n; and this\n',
        )

    def test_colon_separators(self):
        original = '[ci]\naws_access_key_id: a\naws_secret_access_key:b\n'
        self.assertEqual(self.remove_keys(original), '')

    def test_crlf_lines_are_written_with_the_platform_line_ending(self):
        # Every update_config writes the platform's line endings (text
        # mode), LF outside Windows; this pins it for this path too.
        with open(self.filename, 'w', newline='') as f:
            f.write(
                '[a]\r\nx = 1\r\n'
                '[ci]\r\naws_access_key_id = a\r\n'
                'aws_secret_access_key = b\r\n'
            )
        self.writer.update_config(
            dict(self.KEYS, __section__='ci'),
            self.filename,
            remove_empty_section=True,
        )
        with open(self.filename, 'rb') as f:
            self.assertEqual(
                f.read(),
                b'[a]\nx = 1\n'.replace(b'\n', os.linesep.encode()),
            )

    def test_a_continuation_line_is_not_the_header(self):
        # botocore reads "  [ci]" as part of a's x value, so the real [ci]
        # is the one that goes.
        original = (
            '[a]\nx = 1\n  [ci]\n'
            '[ci]\naws_access_key_id = a\naws_secret_access_key = b\n'
        )
        self.assertEqual(self.remove_keys(original), '[a]\nx = 1\n  [ci]\n')

    def test_empty_section_stays_by_default(self):
        original = '[ci]\naws_access_key_id = a\naws_secret_access_key = b\n'
        with open(self.filename, 'w') as f:
            f.write(original)
        self.writer.update_config(
            dict(self.KEYS, __section__='ci'), self.filename
        )
        with open(self.filename) as f:
            self.assertEqual(f.read(), '[ci]\n')

    @skip_if_windows('File mode is POSIX only.')
    def test_file_mode_is_kept(self):
        with open(self.filename, 'w') as f:
            f.write('[ci]\naws_access_key_id = a\n')
        os.chmod(self.filename, 0o600)
        self.remove_keys('[ci]\naws_access_key_id = a\n')
        self.assertEqual(os.stat(self.filename).st_mode & 0o777, 0o600)
