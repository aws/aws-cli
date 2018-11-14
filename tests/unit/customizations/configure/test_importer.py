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
import mock

from . import FakeSession
from awscli.testutils import unittest
from awscli.compat import six
from awscli.customizations.configure.importer import (
    CredentialImporter,
    ConfigureImportCommand,
    CSVCredentialParser,
    CredentialParserError,
)
from awscli.customizations.configure.writer import ConfigFileWriter

CSV_HEADERS = (
    'User name,Password,Access key ID,Secret access key,Console login link\n'
)


class TestConfigureImportCommand(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession({'config_file': 'myconfigfile'})
        self.fake_credentials_filename = os.path.expanduser(
            '~/fake_credentials_filename')
        self.session.profile = None
        self.mock_writer = mock.Mock(spec=ConfigFileWriter)
        self.importer = CredentialImporter(self.mock_writer)
        self.stdout = six.StringIO()
        self.import_command = ConfigureImportCommand(
            self.session,
            importer=self.importer,
            out_stream=self.stdout,
        )

    def _assert_expected_profile(self, args, profile):
        self.import_command(args=args, parsed_globals=None)
        update_args, _ = self.mock_writer.update_config.call_args
        self.assertEqual(update_args[0], profile)
        self.assertIn('/fake_credentials_filename', update_args[1])
        self.assertIn('Successfully imported 1 profile', self.stdout.getvalue())

    def test_import_downloaded_csv(self):
        row = 'PROFILENAME,PW,AKID,SAK,https://console.link\n'
        content = CSV_HEADERS + row
        expected_profile = {
            '__section__': 'PROFILENAME',
            'aws_access_key_id': 'AKID',
            'aws_secret_access_key': 'SAK',
        }
        self._assert_expected_profile(['--csv', content], expected_profile)

    def test_import_downloaded_csv_custom_prefix(self):
        row = 'PROFILENAME,PW,AKID,SAK,https://console.link\n'
        content = CSV_HEADERS + row
        args = ['--csv', content, '--profile-prefix', 'foo-']
        expected_profile = {
            '__section__': 'foo-PROFILENAME',
            'aws_access_key_id': 'AKID',
            'aws_secret_access_key': 'SAK',
        }
        self._assert_expected_profile(args, expected_profile)

    def test_import_downloaded_csv_multiple(self):
        content = (
            'User name,Access key ID,Secret access key\n'
            'PROFILENAME1,AKID1,SAK1\n'
            'PROFILENAME2,AKID2,SAK2\n'
        )
        self.import_command(args=['--csv', content], parsed_globals=None)
        self.assertEqual(self.mock_writer.update_config.call_count, 2)
        self.assertIn('Successfully imported 2 profile', self.stdout.getvalue())

    def test_import_downloaded_bad_headers(self):
        content = 'User name,Secret access key\n'
        with self.assertRaises(CredentialParserError):
            self.import_command(args=['--csv', content], parsed_globals=None)


class TestCSVCredentialParser(unittest.TestCase):
    def setUp(self):
        self.parser = CSVCredentialParser()
        self.expected_credentials = [('PROFILENAME', 'AKID', 'SAK')]

    def assert_parse_matches_expected(self, contents):
        credentials = self.parser.parse_credentials(contents)
        self.assertEqual(credentials, self.expected_credentials)

    def test_csv_parser_downloaded_csv(self):
        row = 'PROFILENAME,PW,AKID,SAK,https://console.link\n'
        self.assert_parse_matches_expected(CSV_HEADERS + row)

    def test_csv_parser_simple(self):
        contents = (
            'User name,Access key ID,Secret access key\n'
            'PROFILENAME,AKID,SAK\n'
        )
        self.assert_parse_matches_expected(contents)

    def test_csv_parser_multiple_entries(self):
        contents = (
            'User name,Access key ID,Secret access key\n'
            'PROFILENAME1,AKID1,SAK1\n'
            'PROFILENAME2,AKID2,SAK2\n'
        )
        self.expected_credentials = [
            ('PROFILENAME1', 'AKID1', 'SAK1'),
            ('PROFILENAME2', 'AKID2', 'SAK2'),
        ]
        self.assert_parse_matches_expected(contents)

    def test_csv_parser_multiple_entries_with_bad_entries(self):
        self.parser.strict = False
        contents = (
            'User name,Access key ID,Secret access key\n'
            'PROFILENAME1,AKID1,SAK1\n'
            'PROFILENAME,,SAK\n'
            'PROFILENAME,AKID,\n'
            ',AKID,SAK\n'
            'PROFILENAME2,AKID2,SAK2\n'
        )
        self.expected_credentials = [
            ('PROFILENAME1', 'AKID1', 'SAK1'),
            ('PROFILENAME2', 'AKID2', 'SAK2'),
        ]
        self.assert_parse_matches_expected(contents)

    def test_csv_parser_header_reorder(self):
        contents = (
            'Access key ID,Secret access key, User name\n'
            'AKID,SAK,PROFILENAME\n'
        )
        self.assert_parse_matches_expected(contents)

    def test_csv_parser_header_case_insensitive(self):
        contents = (
            'access key id,secret access key, user name\n'
            'AKID,SAK,PROFILENAME\n'
        )
        self.assert_parse_matches_expected(contents)

    def test_csv_parser_header_whitespace_insensitive(self):
        contents = (
            '  user name,  access key id,  secret access key    \n'
            'PROFILENAME,AKID,SAK,PROFILENAME\n'
        )
        self.assert_parse_matches_expected(contents)

    def test_csv_parser_values_whitespace_insensitive(self):
        contents = (
            'User name,Access key ID,Secret access key\n'
            '   PROFILENAME   , AKID   ,    SAK  \n'
        )
        self.assert_parse_matches_expected(contents)

    def test_csv_parser_empty_contents(self):
        with self.assertRaises(CredentialParserError):
            self.parser.parse_credentials(' ')

    def test_csv_parser_no_username(self):
        row = ',PW,AKID,SAK,https://console.link\n'
        with self.assertRaises(CredentialParserError):
            self.parser.parse_credentials(CSV_HEADERS + row)

    def test_csv_parser_no_username_header(self):
        contents = 'Access key ID,Secret access key\n'
        with self.assertRaises(CredentialParserError):
            self.parser.parse_credentials(contents)

    def test_csv_parser_no_akid(self):
        row = 'PROFILENAME,PW,,SAK,https://console.link\n'
        with self.assertRaises(CredentialParserError):
            self.parser.parse_credentials(CSV_HEADERS + row)

    def test_csv_parser_no_akid_header(self):
        contents = 'User name,Secret access key\n'
        with self.assertRaises(CredentialParserError):
            self.parser.parse_credentials(contents)

    def test_csv_parser_no_sak(self):
        row = 'PROFILENAME,PW,AKID,,https://console.link\n'
        with self.assertRaises(CredentialParserError):
            self.parser.parse_credentials(CSV_HEADERS + row)

    def test_csv_parser_no_sak_header(self):
        contents = 'User name,Access key ID\n'
        with self.assertRaises(CredentialParserError):
            self.parser.parse_credentials(contents)


class TestCredentialImporter(unittest.TestCase):
    def setUp(self):
        self.mock_writer = mock.Mock(spec=ConfigFileWriter)
        self.importer = CredentialImporter(self.mock_writer)

    def test_import_profile(self):
        file = 'credentials_file'
        credential = ('USERNAME', 'AKID', 'SAK')
        self.importer.import_credential(credential, file)
        profile = {
            '__section__': 'USERNAME',
            'aws_access_key_id': 'AKID',
            'aws_secret_access_key': 'SAK',
        }
        self.mock_writer.update_config.assert_called_with(profile, file)

    def test_import_profile_with_prefix(self):
        file = 'credentials_file'
        credential = ('USERNAME', 'AKID', 'SAK')
        self.importer.import_credential(credential, file, profile_prefix='a-')
        profile = {
            '__section__': 'a-USERNAME',
            'aws_access_key_id': 'AKID',
            'aws_secret_access_key': 'SAK',
        }
        self.mock_writer.update_config.assert_called_with(profile, file)
