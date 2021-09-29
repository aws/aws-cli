# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0e
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import argparse
import os
import sys

import mock
from mock import patch, Mock, MagicMock

import botocore.session
from awscli.customizations.s3.s3 import S3
from awscli.customizations.s3.subcommands import CommandParameters, \
    CommandArchitecture, CpCommand, SyncCommand, ListCommand, RbCommand
from awscli.customizations.s3.transferconfig import RuntimeConfig
from awscli.customizations.s3.syncstrategy.base import \
    SizeAndLastModifiedSync, NeverSync, MissingFileSync
from awscli.customizations.exceptions import ParamValidationError
from awscli.testutils import unittest, BaseAWSHelpOutputTest, \
    BaseAWSCommandParamsTest, FileCreator
from tests.unit.customizations.s3 import make_loc_files, clean_loc_files
from awscli.compat import StringIO


class FakeArgs(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __contains__(self, key):
        return key in self.__dict__


class TestRbCommand(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.session.get_scoped_config.return_value = {}
        self.rb_command = RbCommand(self.session)
        self.parsed_args = FakeArgs(path='s3://mybucket/',
                                    force=True, dir_op=False)
        self.parsed_globals = FakeArgs(region=None, endpoint_url=None,
                                       verify_ssl=None)
        self.cmd_name = 'awscli.customizations.s3.subcommands.RmCommand'
        self.arch_name = 'awscli.customizations.s3.subcommands.CommandArchitecture'

    def test_rb_command_with_force_deletes_objects_in_bucket(self):
        with mock.patch(self.cmd_name) as rm_command:
            with mock.patch(self.arch_name):
                # RmCommand returns an RmCommand instance whose __call__
                # should be the RC of the command.
                # In this case we'll have it return an RC of 0 which indicates
                # success.
                rm_command.return_value.return_value = 0
                self.rb_command._run_main(self.parsed_args,
                                          parsed_globals=self.parsed_globals)
            # Because of --force we should have called the
            # rm_command with the --recursive option.
            rm_command.return_value.assert_called_with(
                ['s3://mybucket/', '--recursive'], mock.ANY)

    def test_rb_command_with_force_requires_strict_path(self):
        with self.assertRaises(ParamValidationError):
            self.parsed_args.path = 's3://mybucket/mykey'
            self.rb_command._run_main(self.parsed_args,
                                      parsed_globals=self.parsed_globals)


class TestLSCommand(unittest.TestCase):
    def setUp(self):
        self.session = mock.Mock()
        self.session.create_client.return_value.list_buckets.return_value\
            = {'Buckets': []}
        self.session.create_client.return_value.get_paginator.return_value\
            .paginate.return_value = [{'Contents': [], 'CommonPrefixes': []}]

    def test_ls_command_for_bucket(self):
        ls_command = ListCommand(self.session)
        parsed_args = FakeArgs(paths='s3://mybucket/', dir_op=False,
                               page_size='5', human_readable=False,
                               summarize=False, request_payer=None)
        parsed_globals = mock.Mock()
        ls_command._run_main(parsed_args, parsed_globals)
        call = self.session.create_client.return_value.list_objects_v2
        paginate = self.session.create_client.return_value.get_paginator\
            .return_value.paginate
        # We should make no operation calls.
        self.assertEqual(call.call_count, 0)
        # And only a single pagination call to ListObjectsV2.
        self.session.create_client.return_value.get_paginator.\
            assert_called_with('list_objects_v2')
        ref_call_args = {'Bucket': u'mybucket', 'Delimiter': '/',
                         'Prefix': u'',
                         'PaginationConfig': {'PageSize': u'5'}}

        paginate.assert_called_with(**ref_call_args)

    def test_ls_command_with_no_args(self):
        ls_command = ListCommand(self.session)
        parsed_global = FakeArgs(region=None, endpoint_url=None,
                                 verify_ssl=None)
        parsed_args = FakeArgs(dir_op=False, paths='s3://',
                               human_readable=False, summarize=False,
                               request_payer=None)
        ls_command._run_main(parsed_args, parsed_global)
        # We should only be a single call.
        call = self.session.create_client.return_value.list_buckets
        self.assertTrue(call.called)
        self.assertEqual(call.call_count, 1)
        self.assertEqual(call.call_args[1], {})
        # Verify get_client
        get_client = self.session.create_client
        args = get_client.call_args
        self.assertEqual(
            args,
            mock.call('s3', region_name=None, verify=None, endpoint_url=None)
        )

    def test_ls_with_verify_argument(self):
        options = {'default': 's3://', 'nargs': '?'}
        ls_command = ListCommand(self.session)
        parsed_global = FakeArgs(region='us-west-2', endpoint_url=None,
                                 verify_ssl=False)
        parsed_args = FakeArgs(paths='s3://', dir_op=False,
                               human_readable=False, summarize=False,
                               request_payer=None)
        ls_command._run_main(parsed_args, parsed_global)
        # Verify get_client
        get_client = self.session.create_client
        args = get_client.call_args
        self.assertEqual(
            args,
            mock.call(
                's3', region_name='us-west-2', verify=False, endpoint_url=None,
            )
        )

    def test_ls_with_requester_pays(self):
        ls_command = ListCommand(self.session)
        parsed_args = FakeArgs(paths='s3://mybucket/', dir_op=False,
                               human_readable=False, summarize=False,
                               request_payer='requester', page_size='5')
        parsed_globals = mock.Mock()
        ls_command._run_main(parsed_args, parsed_globals)
        call = self.session.create_client.return_value.list_objects
        paginate = self.session.create_client.return_value.get_paginator\
            .return_value.paginate
        # We should make no operation calls.
        self.assertEqual(call.call_count, 0)
        # And only a single pagination call to ListObjectsV2.
        self.session.create_client.return_value.get_paginator.\
            assert_called_with('list_objects_v2')
        ref_call_args = {
            'Bucket': u'mybucket', 'Delimiter': '/',
            'Prefix': u'', 'PaginationConfig': {'PageSize': '5'},
            'RequestPayer': 'requester',
        }

        paginate.assert_called_with(**ref_call_args)


class CommandArchitectureTest(BaseAWSCommandParamsTest):
    def setUp(self):
        super(CommandArchitectureTest, self).setUp()
        self.session = self.driver.session
        self.bucket = 'mybucket'
        self.transfer_manager = Mock()
        self.source_client = Mock()
        self.transfer_client = Mock()
        self.file_creator = FileCreator()
        self.loc_files = make_loc_files(self.file_creator)
        self.output = StringIO()
        self.err_output = StringIO()
        self.saved_stdout = sys.stdout
        self.saved_stderr = sys.stderr
        sys.stdout = self.output
        sys.stderr = self.err_output

    def tearDown(self):
        self.output.close()
        self.err_output.close()
        sys.stdout = self.saved_stdout
        sys.stderr = self.saved_stderr

        super(CommandArchitectureTest, self).tearDown()
        clean_loc_files(self.file_creator)

    def get_cmd_architecture(self, cmd, params):
        return CommandArchitecture(
            session=self.session,
            cmd=cmd,
            parameters=params,
            transfer_manager=self.transfer_manager,
            source_client=self.source_client,
            transfer_client=self.transfer_client,
        )

    def get_params(self, **override_kwargs):
        params = {
            'region': 'us-east-1',
            'endpoint_url': None,
            'verify_ssl': None,
            'is_stream': False
        }
        params.update(override_kwargs)
        return params

    def test_create_instructions(self):
        """
        This tests to make sure the instructions for any command is generated
        properly.
        """
        cmds = ['cp', 'mv', 'rm', 'sync']

        instructions = {'cp': ['file_generator', 'file_info_builder',
                               's3_handler'],
                        'mv': ['file_generator', 'file_info_builder',
                               's3_handler'],
                        'rm': ['file_generator', 'file_info_builder',
                               's3_handler'],
                        'sync': ['file_generator', 'comparator',
                                 'file_info_builder', 's3_handler']}

        params = {'filters': True, 'region': 'us-east-1', 'endpoint_url': None,
                  'verify_ssl': None, 'is_stream': False}
        for cmd in cmds:
            cmd_arc = self.get_cmd_architecture(cmd, self.get_params())
            cmd_arc.create_instructions()
            self.assertEqual(cmd_arc.instructions, instructions[cmd])

        # Test if there is a filter.
        cmd_arc = self.get_cmd_architecture('cp', params)
        cmd_arc.create_instructions()
        self.assertEqual(cmd_arc.instructions, ['file_generator', 'filters',
                                                'file_info_builder',
                                                's3_handler'])

    def test_choose_sync_strategy_default(self):
        self.session = Mock(self.session)
        cmd_arc = self.get_cmd_architecture('sync', self.get_params())
        # Check if no plugins return their sync strategy.  Should
        # result in the default strategies
        self.session.emit.return_value = None
        sync_strategies = cmd_arc.choose_sync_strategies()
        self.assertEqual(
            sync_strategies['file_at_src_and_dest_sync_strategy'].__class__,
            SizeAndLastModifiedSync
        )
        self.assertEqual(
            sync_strategies['file_not_at_dest_sync_strategy'].__class__,
            MissingFileSync
        )
        self.assertEqual(
            sync_strategies['file_not_at_src_sync_strategy'].__class__,
            NeverSync
        )

    def test_choose_sync_strategy_overwrite(self):
        self.session = Mock(self.session)
        cmd_arc = self.get_cmd_architecture('sync', self.get_params())
        # Check that the default sync strategy is overwritted if a plugin
        # returns its sync strategy.
        mock_strategy = Mock()
        mock_strategy.sync_type = 'file_at_src_and_dest'

        mock_not_at_dest_sync_strategy = Mock()
        mock_not_at_dest_sync_strategy.sync_type = 'file_not_at_dest'

        mock_not_at_src_sync_strategy = Mock()
        mock_not_at_src_sync_strategy.sync_type = 'file_not_at_src'

        responses = [(None, mock_strategy),
                     (None, mock_not_at_dest_sync_strategy),
                     (None, mock_not_at_src_sync_strategy)]

        self.session.emit.return_value = responses
        sync_strategies = cmd_arc.choose_sync_strategies()
        self.assertEqual(
            sync_strategies['file_at_src_and_dest_sync_strategy'],
            mock_strategy
        )
        self.assertEqual(
            sync_strategies['file_not_at_dest_sync_strategy'],
            mock_not_at_dest_sync_strategy
        )
        self.assertEqual(
            sync_strategies['file_not_at_src_sync_strategy'],
            mock_not_at_src_sync_strategy
        )


class CommandParametersTest(unittest.TestCase):
    def setUp(self):
        self.environ = {}
        self.environ_patch = patch('os.environ', self.environ)
        self.environ_patch.start()
        self.mock = MagicMock()
        self.mock.get_config = MagicMock(return_value={'region': None})
        self.file_creator = FileCreator()
        self.loc_files = make_loc_files(self.file_creator)
        self.bucket = 's3testbucket'

    def tearDown(self):
        self.environ_patch.stop()
        clean_loc_files(self.file_creator)

    def test_check_path_type_pass(self):
        # This tests the class's ability to determine whether the correct
        # path types have been passed for a particular command.  It test every
        # possible combination that is correct for every command.
        cmds = {'cp': ['locals3', 's3s3', 's3local'],
                'mv': ['locals3', 's3s3', 's3local'],
                'rm': ['s3'], 'mb': ['s3'], 'rb': ['s3'],
                'sync': ['locals3', 's3s3', 's3local']}
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        local_file = self.loc_files[0]

        combos = {'s3s3': [s3_file, s3_file],
                  's3local': [s3_file, local_file],
                  'locals3': [local_file, s3_file],
                  's3': [s3_file],
                  'local': [local_file],
                  'locallocal': [local_file, local_file]}

        for cmd in cmds.keys():
            cmd_param = CommandParameters(cmd, {}, '')
            cmd_param.add_region(mock.Mock())
            correct_paths = cmds[cmd]
            for path_args in correct_paths:
                cmd_param.check_path_type(combos[path_args])

    def test_check_path_type_fail(self):
        # This tests the class's ability to determine whether the correct
        # path types have been passed for a particular command. It test every
        # possible combination that is incorrect for every command.
        cmds = {'cp': ['local', 'locallocal', 's3'],
                'mv': ['local', 'locallocal', 's3'],
                'rm': ['local', 'locallocal', 's3s3', 'locals3', 's3local'],
                'ls': ['local', 'locallocal', 's3s3', 'locals3', 's3local'],
                'sync': ['local', 'locallocal', 's3'],
                'mb': ['local', 'locallocal', 's3s3', 'locals3', 's3local'],
                'rb': ['local', 'locallocal', 's3s3', 'locals3', 's3local']}
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        local_file = self.loc_files[0]

        combos = {'s3s3': [s3_file, s3_file],
                  's3local': [s3_file, local_file],
                  'locals3': [local_file, s3_file],
                  's3': [s3_file],
                  'local': [local_file],
                  'locallocal': [local_file, local_file]}

        for cmd in cmds.keys():
            cmd_param = CommandParameters(cmd, {}, '')
            cmd_param.add_region(mock.Mock())
            wrong_paths = cmds[cmd]
            for path_args in wrong_paths:
                with self.assertRaises(ParamValidationError):
                    cmd_param.check_path_type(combos[path_args])

    def test_validate_streaming_paths_upload(self):
        paths = ['-', 's3://bucket']
        cmd_params = CommandParameters('cp', {}, '')
        cmd_params.add_paths(paths)
        self.assertTrue(cmd_params.parameters['is_stream'])
        self.assertTrue(cmd_params.parameters['only_show_errors'])
        self.assertFalse(cmd_params.parameters['dir_op'])

    def test_validate_streaming_paths_download(self):
        paths = ['s3://bucket/key', '-']
        cmd_params = CommandParameters('cp', {}, '')
        cmd_params.add_paths(paths)
        self.assertTrue(cmd_params.parameters['is_stream'])
        self.assertTrue(cmd_params.parameters['only_show_errors'])
        self.assertFalse(cmd_params.parameters['dir_op'])

    def test_validate_no_streaming_paths(self):
        paths = [self.file_creator.rootdir, 's3://bucket']
        cmd_params = CommandParameters('cp', {}, '')
        cmd_params.add_paths(paths)
        self.assertFalse(cmd_params.parameters['is_stream'])

    def test_validate_streaming_paths_error(self):
        parameters = {'src': '-', 'dest': 's3://bucket'}
        cmd_params = CommandParameters('sync', parameters, '')
        with self.assertRaises(ParamValidationError):
            cmd_params._validate_streaming_paths()

    def test_validate_non_existent_local_path_upload(self):
        non_existent_path = os.path.join(self.file_creator.rootdir, 'foo')
        paths = [non_existent_path, 's3://bucket/']
        cmd_param = CommandParameters('cp', {}, '')
        with self.assertRaises(RuntimeError):
            cmd_param.add_paths(paths)

    def test_add_path_for_non_existsent_local_path_download(self):
        non_existent_path = os.path.join(self.file_creator.rootdir, 'foo')
        paths = ['s3://bucket', non_existent_path]
        cmd_param = CommandParameters('cp', {'dir_op': True}, '')
        cmd_param.add_paths(paths)
        self.assertTrue(os.path.exists(non_existent_path))

    def test_validate_sse_c_args_missing_sse(self):
        paths = ['s3://bucket/foo', 's3://bucket/bar']
        params = {'dir_op': False, 'sse_c_key': 'foo'}
        cmd_param = CommandParameters('cp', params, '')
        error_msg = '--sse-c must be specified'
        with self.assertRaisesRegexp(ParamValidationError, error_msg):
            cmd_param.add_paths(paths)

    def test_validate_sse_c_args_missing_sse_c_key(self):
        paths = ['s3://bucket/foo', 's3://bucket/bar']
        params = {'dir_op': False, 'sse_c': 'AES256'}
        cmd_param = CommandParameters('cp', params, '')
        error_msg = '--sse-c-key must be specified'
        with self.assertRaisesRegexp(ParamValidationError, error_msg):
            cmd_param.add_paths(paths)

    def test_validate_sse_c_args_missing_sse_c_copy_source(self):
        paths = ['s3://bucket/foo', 's3://bucket/bar']
        params = {'dir_op': False, 'sse_c_copy_source_key': 'foo'}
        cmd_param = CommandParameters('cp', params, '')
        error_msg = '--sse-c-copy-source must be specified'
        with self.assertRaisesRegexp(ParamValidationError, error_msg):
            cmd_param.add_paths(paths)

    def test_validate_sse_c_args_missing_sse_c_copy_source_key(self):
        paths = ['s3://bucket/foo', 's3://bucket/bar']
        params = {'dir_op': False, 'sse_c_copy_source': 'AES256'}
        cmd_param = CommandParameters('cp', params, '')
        error_msg = '--sse-c-copy-source-key must be specified'
        with self.assertRaisesRegexp(ParamValidationError, error_msg):
            cmd_param.add_paths(paths)

    def test_validate_sse_c_args_wrong_path_type(self):
        paths = ['s3://bucket/foo', self.file_creator.rootdir]
        params = {'dir_op': False, 'sse_c_copy_source': 'AES256',
                  'sse_c_copy_source_key': 'foo'}
        cmd_param = CommandParameters('cp', params, '')
        error_msg = 'only supported for copy operations'
        with self.assertRaisesRegexp(ParamValidationError, error_msg):
            cmd_param.add_paths(paths)

    def test_adds_is_move(self):
        params = {}
        CommandParameters('mv', params, '')
        self.assertTrue(params.get('is_move'))

        # is_move should only be true for mv
        params = {}
        CommandParameters('cp', params, '')
        self.assertFalse(params.get('is_move'))


class HelpDocTest(BaseAWSHelpOutputTest):
    def setUp(self):
        super(HelpDocTest, self).setUp()
        self.session = botocore.session.get_session()

    def tearDown(self):
        super(HelpDocTest, self).tearDown()

    def test_s3_help(self):
        # This tests the help command for the s3 service. This
        # checks to make sure the appropriate descriptions are
        # added including the tutorial.
        s3 = S3(self.session)
        parser = argparse.ArgumentParser()
        parser.add_argument('--paginate', action='store_true')
        parsed_global = parser.parse_args(['--paginate'])
        help_command = s3.create_help_command()
        help_command([], parsed_global)
        self.assert_contains(
            "This section explains prominent concepts "
            "and notations in the set of high-level S3 commands provided.")
        self.assert_contains("Every command takes one or two positional")
        self.assert_contains("* rb")

    def test_s3command_help(self):
        # This tests the help command for an s3 command. This
        # checks to make sure the command prints appropriate
        # parts.  Note the examples are not included because
        # the event was not registered.
        s3command = CpCommand(self.session)
        s3command._arg_table = s3command._build_arg_table()
        parser = argparse.ArgumentParser()
        parser.add_argument('--paginate', action='store_true')
        parsed_global = parser.parse_args(['--paginate'])
        help_command = s3command.create_help_command()
        help_command([], parsed_global)
        self.assert_contains("cp")
        self.assert_contains("[--acl <value>]")
        self.assert_contains("Displays the operations that would be")

    def test_help(self):
        # This ensures that the file appropriately redirects to help object
        # if help is the only argument left to be parsed.  There should not
        # have any contents in the docs.
        s3_command = SyncCommand(self.session)
        s3_command(['help'], [])
        self.assert_contains('sync')
        self.assert_contains("Synopsis")


if __name__ == "__main__":
    unittest.main()
