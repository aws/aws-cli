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
import io
import argparse
from botocore.exceptions import ClientError

from awscli.customizations import utils
from awscli.testutils import mock
from awscli.testutils import unittest
from awscli.testutils import BaseAWSHelpOutputTest


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


class TestCommandTableAlias(BaseAWSHelpOutputTest):

    def test_alias_command_table(self):
        old_name = 'cloudhsmv2'
        new_name = 'nopossiblewaythisisalreadythere'

        def handler(command_table, **kwargs):
            utils.alias_command(command_table, old_name, new_name)

        self._assert_command_exists(old_name, handler)
        self._assert_command_exists(new_name, handler)

        # Verify that the new name is documented
        self.driver.main(['help'])
        self.assert_contains(new_name)
        self.assert_not_contains(old_name)

    def test_make_hidden_alias(self):
        old_name = 'cloudhsmv2'
        new_name = 'nopossiblewaythisisalreadythere'

        def handler(command_table, **kwargs):
            utils.make_hidden_command_alias(command_table, old_name, new_name)

        self._assert_command_exists(old_name, handler)
        self._assert_command_exists(new_name, handler)

        # Verify that the new isn't documented
        self.driver.main(['help'])
        self.assert_not_contains(new_name)
        self.assert_contains(old_name)

    def _assert_command_exists(self, command_name, handler):
        # Verify that we can alias a top level command.
        self.session.register('building-command-table.main', handler)
        self.driver.main([command_name, 'help'])
        self.assert_contains(command_name)

        # We can also see subcommands help as well.
        self.driver.main([command_name, 'describe-clusters', 'help'])
        self.assert_contains('describe-clusters')


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


class MockPipedStdout(io.BytesIO):
    """Mocks `sys.stdout`.

    We can't use `TextIOWrapper` because calling
    `TextIOWrapper(.., encoding=None)` sets the ``encoding`` attribute to
    `UTF-8`. The attribute is also `readonly` in `TextIOWrapper` and
    `TextIOBase` so it cannot be overwritten in subclasses.
    """
    def __init__(self):
        self.encoding = None

        super(MockPipedStdout, self).__init__()

    def write(self, data):
        # sys.stdout.write() will default to encoding to ascii, when its
        # `encoding` is `None`.
        if self.encoding is None:
            data = data.encode('ascii')
        else:
            data = data.encode(self.encoding)
        super(MockPipedStdout, self).write(data)


class TestUniPrint(unittest.TestCase):

    def test_out_file_with_encoding_attribute(self):
        buf = io.BytesIO()
        out = io.TextIOWrapper(buf, encoding='utf-8')
        utils.uni_print(u'\u2713', out)
        self.assertEqual(buf.getvalue(), u'\u2713'.encode('utf-8'))

    def test_encoding_with_encoding_none(self):
        '''When the output of the aws command is being piped,
        the `encoding` attribute of `sys.stdout` is `None`.'''
        out = MockPipedStdout()
        utils.uni_print(u'SomeChars\u2713\u2714OtherChars', out)
        self.assertEqual(out.getvalue(), b'SomeChars??OtherChars')

    def test_encoding_statement_fails_are_replaced(self):
        buf = io.BytesIO()
        out = io.TextIOWrapper(buf, encoding='ascii')
        utils.uni_print(u'SomeChars\u2713\u2714OtherChars', out)
        # We replace the characters that can't be encoded
        # with '?'.
        self.assertEqual(buf.getvalue(), b'SomeChars??OtherChars')


class TestGetPolicyARNSuffix(unittest.TestCase):
    def test_get_policy_arn_suffix(self):
        self.assertEqual("aws-cn", utils.get_policy_arn_suffix("cn-northwest-1"))
        self.assertEqual("aws-cn", utils.get_policy_arn_suffix("cn-northwest-2"))
        self.assertEqual("aws-cn", utils.get_policy_arn_suffix("cn-north-1"))
        self.assertEqual("aws-us-gov", utils.get_policy_arn_suffix("us-gov-west-1"))
        self.assertEqual("aws", utils.get_policy_arn_suffix("ca-central-1"))
        self.assertEqual("aws", utils.get_policy_arn_suffix("us-east-1"))
        self.assertEqual("aws", utils.get_policy_arn_suffix("sa-east-1"))
        self.assertEqual("aws", utils.get_policy_arn_suffix("ap-south-1"))
