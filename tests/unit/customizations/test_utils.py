# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from awscli.testutils import unittest
from awscli.testutils import BaseAWSHelpOutputTest

import argparse
import mock
from botocore.exceptions import ClientError

from awscli.customizations import utils


class FakeParsedArgs(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class TestCommandTableRenames(BaseAWSHelpOutputTest):

    def test_rename_command_table(self):
        handler = lambda command_table, **kwargs: utils.rename_command(
            command_table, 'ec2', 'fooec2')
        # Verify that we can rename a top level command.
        self.session.register('building-command-table.main', handler)
        self.driver.main(['fooec2', 'help'])
        self.assert_contains('fooec2')

        # We can also see subcommands help as well.
        self.driver.main(['fooec2', 'run-instances', 'help'])
        self.assert_contains('run-instances')


class TestHiddenAlias(unittest.TestCase):
    def test_not_marked_as_required_if_not_needed(self):
        original_arg_required = mock.Mock()
        original_arg_required.required = False
        arg_table = {'original': original_arg_required}
        utils.make_hidden_alias(arg_table, 'original', 'new-name')
        self.assertIn('new-name', arg_table)
        # Note: the _DOCUMENT_AS_REQUIRED is tested as a functional
        # test because it only affects how the doc synopsis is
        # rendered.
        self.assertFalse(arg_table['original'].required)
        self.assertFalse(arg_table['new-name'].required)

    def test_hidden_alias_marks_as_not_required(self):
        original_arg_required = mock.Mock()
        original_arg_required.required = True
        arg_table = {'original': original_arg_required}
        utils.make_hidden_alias(arg_table, 'original', 'new-name')
        self.assertIn('new-name', arg_table)
        self.assertFalse(arg_table['original'].required)
        self.assertFalse(arg_table['new-name'].required)


class TestValidateMututuallyExclusiveGroups(unittest.TestCase):
    def test_two_single_groups(self):
        # The most basic example of mutually exclusive args.
        # If foo is specified, but bar is not, then we're fine.
        parsed = FakeParsedArgs(foo='one', bar=None)
        utils.validate_mutually_exclusive(parsed, ['foo'], ['bar'])
        # If bar is specified and foo is not, then we're fine.
        parsed = FakeParsedArgs(foo=None, bar='one')
        utils.validate_mutually_exclusive(parsed, ['foo'], ['bar'])
        # But if we specify both foo and bar then we get an error.
        parsed = FakeParsedArgs(foo='one', bar='two')
        with self.assertRaises(ValueError):
            utils.validate_mutually_exclusive(parsed, ['foo'], ['bar'])

    def test_multiple_groups(self):
        groups = (['one', 'two', 'three'], ['foo', 'bar', 'baz'],
                  ['qux', 'bad', 'morebad'])
        # This is fine.
        parsed = FakeParsedArgs(foo='foo', bar='bar', baz='baz')
        utils.validate_mutually_exclusive(parsed, *groups)
        # But this is bad.
        parsed = FakeParsedArgs(foo='one', bar=None, qux='three')
        with self.assertRaises(ValueError):
            utils.validate_mutually_exclusive(parsed, *groups)


class TestS3BucketExists(unittest.TestCase):
    def setUp(self):
        self.s3_client = mock.Mock()
        self.bucket_name = 'mybucket'
        self.error_response = {
            'Error': {
                'Code': '404',
                'Message': 'Not Found'
            }
        }
        self.bucket_no_exists_error = ClientError(
            self.error_response,
            'HeadBucket'
        )

    def test_bucket_exists(self):
        self.assertTrue(
            utils.s3_bucket_exists(self.s3_client, self.bucket_name))

    def test_bucket_not_exists(self):
        self.s3_client.head_bucket.side_effect = self.bucket_no_exists_error
        self.assertFalse(
            utils.s3_bucket_exists(self.s3_client, self.bucket_name))

    def test_bucket_exists_with_non_404(self):
        self.error_response['Error']['Code'] = '403'
        self.error_response['Error']['Message'] = 'Forbidden'
        forbidden_error = ClientError(self.error_response, 'HeadBucket')
        self.s3_client.head_bucket.side_effect = forbidden_error
        self.assertTrue(
            utils.s3_bucket_exists(self.s3_client, self.bucket_name))


class TestClientCreationFromGlobals(unittest.TestCase):
    def setUp(self):
        self.fake_client = {}
        self.session = mock.Mock()
        self.session.create_client.return_value = self.fake_client
        self.parsed_globals = argparse.Namespace()
        self.parsed_globals.region = 'us-west-2'
        self.parsed_globals.endpoint_url = 'https://foo.bar.com'
        self.parsed_globals.verify_ssl = False

    def test_creates_clients_with_no_overrides(self):
        client = utils.create_client_from_parsed_globals(
            self.session, 'ec2', self.parsed_globals)
        self.assertEqual(self.fake_client, client)
        self.session.create_client.assert_called_once_with(
            'ec2',
            region_name='us-west-2',
            verify=False,
            endpoint_url='https://foo.bar.com'
        )

    def test_creates_clients_with_overrides(self):
        overrides = {
            'region_name': 'custom',
            'verify': True,
            'other_thing': 'more custom'
        }
        client = utils.create_client_from_parsed_globals(
            self.session, 'ec2', self.parsed_globals, overrides)
        self.assertEqual(self.fake_client, client)
        self.session.create_client.assert_called_once_with(
            'ec2',
            region_name='custom',
            verify=True,
            other_thing='more custom',
            endpoint_url='https://foo.bar.com'
        )

    def test_creates_clients_with_no_parsed_globals(self):
        client = utils.create_client_from_parsed_globals(
            self.session, 'ec2', argparse.Namespace())
        self.assertEqual(self.fake_client, client)
        self.session.create_client.assert_called_once_with('ec2')
