# Copyright 2013 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
from six import StringIO
import sys
from tests import unittest

import awscli
import botocore.session
from mock import Mock, MagicMock, patch

from awscli.customizations.s3.s3 import AppendFilter, cmd_dict, \
    params_dict, awscli_initialize, add_s3, add_commands, add_cmd_params, \
    S3, S3Command, S3Parameter, CommandArchitecture, CommandParameters
from tests.unit.customizations.s3 import make_loc_files, clean_loc_files, \
    make_s3_files, s3_cleanup, S3HandlerBaseTest
from tests.unit.customizations.s3.fake_session import FakeSession
from tests.unit.docs.test_help_output import CapturedRenderer, \
    BaseAWSHelpOutput


class AppendFilterTest(unittest.TestCase):
    """
    This ensures that the custom action produces the correct format
    for the namespace variable
    """
    def test_call(self):
        parser = argparse.ArgumentParser()

        parser.add_argument('--include', action=AppendFilter, nargs=1,
                            dest='path')
        parser.add_argument('--exclude', action=AppendFilter, nargs=1,
                            dest='path')
        parsed_args = parser.parse_args(['--include', 'a', '--exclude', 'b'])
        self.assertEqual(parsed_args.path, [['--include', 'a'],
                                            ['--exclude', 'b']])


class AWSInitializeTest(unittest.TestCase):
    """
    This test ensures that all events are correctly registered such that
    all of the commands can be run.
    """
    def setUp(self):
        self.cli = Mock()

    def test_initialize(self):
        awscli_initialize(self.cli)
        reference = []
        reference.append("building-command-table.main")
        reference.append("building-operation-table.s3")
        reference.append("doc-examples.S3.*")
        cmds = ['mv', 'rm', 'ls', 'rb', 'mb', 'cp', 'sync']
        for cmd in cmds:
            reference.append("building-parameter-table.s3." + cmd)
        for arg in self.cli.register.call_args_list:
            self.assertIn(arg[0][0], reference)


class CreateTablesTest(unittest.TestCase):
    def test_s3(self):
        """
        Ensures that the table for the service was created properly.
        """
        self.services = {}
        add_s3(self.services, True)
        for service in self.services.keys():
            self.assertIn(service, ['s3'])

    def test_command(self):
        """
        Ensures that all of the commands generated in the table
        are elgible commands.
        """
        self.commands = {}
        commands_list = ['cp', 'mv', 'rm', 'sync', 'ls', 'mb', 'rb']
        add_commands(self.commands, True)
        for command in self.commands.keys():
            self.assertIn(command, commands_list)

    def test_parameters(self):
        """
        Ensures that all of the parameters generated for a specified
        command are an elgible parameter.
        """
        commands_list = ['cp', 'mv', 'rm', 'sync', 'ls', 'mb', 'rb']
        params_list = ['dryrun', 'delete', 'quiet', 'recursive', 'exclude',
                       'include', 'acl', 'force']
        for cmd in commands_list:
            self.parameters = {}
            add_cmd_params(self.parameters, cmd)
            for param in self.parameters.keys():
                self.assertIn(param, params_list)


class S3Test(unittest.TestCase):
    """
    This test to ensure the command object can be called from
    parsing a command in the service object.
    """
    def setUp(self):
        self.mock = MagicMock(return_value='test service')

    def test_call(self):
        session = botocore.session.get_session()
        s3 = S3('s3', session, {'s3': self.mock})
        response = s3(['s3'], [])
        self.assertEqual(response, "test service")


class S3CommandTest(unittest.TestCase):
    """
    This checks top make sure that the S3Command properly handles commands
    passed to it.
    """
    def setUp(self):
        self.session = botocore.session.get_session()
        module = 'awscli.customizations.s3.s3.CommandArchitecture'
        self.cmd_arc_patch = patch(module)
        self.cmd_arc_mock = self.cmd_arc_patch.start()
        self.cmd_arc_mock.run.return_value = "Passed"

    def tearDown(self):
        self.cmd_arc_patch.stop()

    def test_call(self):
        """
        This just checks to make sure no exceptions get thrown for a
        proper command.
        """
        s3_command = S3Command('ls', self.session, {'nargs': 1})
        s3_command(['s3://'], [])

    def test_call_error(self):
        """
        This checks to make sure an improper command throws an
        exception.
        """
        s3_command = S3Command('ls', self.session,  {'nargs': 1})
        with self.assertRaises(Exception):
            s3_command(['s3://', '--sfdf'], [])


class S3ParameterTest(unittest.TestCase):
    """
    Tests the ability to put parameters along with options into
    a parser using the S3Parameter class
    """
    def test_add_to_parser(self):
        s3_param = S3Parameter('test',
                               {'action': 'store_true', 'dest': 'destination'})
        parser = argparse.ArgumentParser()
        s3_param.add_to_parser(parser)
        parsed_args = parser.parse_args(['--test'])
        self.assertEqual(parsed_args.destination, True)


class CommandArchitectureTest(S3HandlerBaseTest):
    def setUp(self):
        super(CommandArchitectureTest, self).setUp()
        self.session = FakeSession()
        self.bucket = make_s3_files(self.session)
        self.loc_files = make_loc_files()
        self.output = StringIO()
        self.saved_stdout = sys.stdout
        sys.stdout = self.output

    def tearDown(self):
        self.output.close()
        sys.stdout = self.saved_stdout
        super(CommandArchitectureTest, self).setUp()
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket, self.session)

    def test_create_instructions(self):
        """
        This tests to make sure the instructions for any command is generated
        properly.
        """
        cmds = ['cp', 'mv', 'rm', 'sync', 'ls', 'mb', 'rb']

        instructions = {'cp': ['file_generator', 's3_handler'],
                        'mv': ['file_generator', 's3_handler'],
                        'rm': ['file_generator', 's3_handler'],
                        'sync': ['file_generator', 'comparator', 's3_handler'],
                        'ls': ['s3_handler'],
                        'mb': ['s3_handler'],
                        'rb': ['s3_handler']}

        params = {'filters': True}
        for cmd in cmds:
            cmd_arc = CommandArchitecture(self.session, cmd, {})
            cmd_arc.create_instructions()
            self.assertEqual(cmd_arc.instructions, instructions[cmd])

        # Test if there is a filter.
        cmd_arc = CommandArchitecture(self.session, 'cp', params)
        cmd_arc.create_instructions()
        self.assertEqual(cmd_arc.instructions, ['file_generator', 'filters',
                                                's3_handler'])

    def test_run_cp_put(self):
        """
        This ensures that the architecture sets up correctly for a ``cp`` put
        command.  It is just just a dry run, but all of the components need
        to be wired correctly for it to work.
        """
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        local_file = self.loc_files[0]
        rel_local_file = os.path.relpath(local_file)
        filters = [['--include', '*']]
        params = {'dir_op': False, 'dryrun': True, 'quiet': False,
                  'src': local_file, 'dest': s3_file, 'filters': filters,
                  'paths_type': 'locals3'}
        cmd_arc = CommandArchitecture(self.session, 'cp', params)
        cmd_arc.create_instructions()
        cmd_arc.run()
        output_str = "(dryrun) upload: %s to %s" % (rel_local_file, s3_file)
        self.assertIn(output_str, self.output.getvalue())

    def test_run_cp_get(self):
        """
        This ensures that the architecture sets up correctly for a ``cp`` get
        command.  It is just just a dry run, but all of the components need
        to be wired correctly for it to work.
        """
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        local_file = self.loc_files[0]
        rel_local_file = os.path.relpath(local_file)
        filters = [['--include', '*']]
        params = {'dir_op': False, 'dryrun': True, 'quiet': False,
                  'src': s3_file, 'dest': local_file, 'filters': filters,
                  'paths_type': 's3local'}
        cmd_arc = CommandArchitecture(self.session, 'cp', params)
        cmd_arc.create_instructions()
        cmd_arc.run()
        output_str = "(dryrun) download: %s to %s" % (s3_file, rel_local_file)
        self.assertIn(output_str, self.output.getvalue())

    def test_run_cp_copy(self):
        """
        This ensures that the architecture sets up correctly for a ``cp`` copy
        command.  It is just just a dry run, but all of the components need
        to be wired correctly for it to work.
        """
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        filters = [['--include', '*']]
        params = {'dir_op': False, 'dryrun': True, 'quiet': False,
                  'src': s3_file, 'dest': s3_file, 'filters': filters,
                  'paths_type': 's3s3'}
        cmd_arc = CommandArchitecture(self.session, 'cp', params)
        cmd_arc.create_instructions()
        cmd_arc.run()
        output_str = "(dryrun) copy: %s to %s" % (s3_file, s3_file)
        self.assertIn(output_str, self.output.getvalue())

    def test_run_mv(self):
        """
        This ensures that the architecture sets up correctly for a ``mv``
        command.  It is just just a dry run, but all of the components need
        to be wired correctly for it to work.
        """
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        filters = [['--include', '*']]
        params = {'dir_op': False, 'dryrun': True, 'quiet': False,
                  'src': s3_file, 'dest': s3_file, 'filters': filters,
                  'paths_type': 's3s3'}
        cmd_arc = CommandArchitecture(self.session, 'mv', params)
        cmd_arc.create_instructions()
        cmd_arc.run()
        output_str = "(dryrun) move: %s to %s" % (s3_file, s3_file)
        self.assertIn(output_str, self.output.getvalue())

    def test_run_remove(self):
        """
        This ensures that the architecture sets up correctly for a ``rm``
        command.  It is just just a dry run, but all of the components need
        to be wired correctly for it to work.
        """
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        filters = [['--include', '*']]
        params = {'dir_op': False, 'dryrun': True, 'quiet': False,
                  'src': s3_file, 'dest': s3_file, 'filters': filters,
                  'paths_type': 's3'}
        cmd_arc = CommandArchitecture(self.session, 'rm', params)
        cmd_arc.create_instructions()
        cmd_arc.run()
        output_str = "(dryrun) delete: %s" % s3_file
        self.assertIn(output_str, self.output.getvalue())

    def test_run_sync(self):
        """
        This ensures that the architecture sets up correctly for a ``sync``
        command.  It is just just a dry run, but all of the components need
        to be wired correctly for it to work.
        """
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        local_file = self.loc_files[0]
        s3_prefix = 's3://' + self.bucket + '/'
        local_dir = self.loc_files[3]
        rel_local_file = os.path.relpath(local_file)
        filters = [['--include', '*']]
        params = {'dir_op': True, 'dryrun': True, 'quiet': False,
                  'src': local_dir, 'dest': s3_prefix, 'filters': filters,
                  'paths_type': 'locals3'}
        cmd_arc = CommandArchitecture(self.session, 'sync', params)
        cmd_arc.create_instructions()
        cmd_arc.run()
        output_str = "(dryrun) upload: %s to %s" % (rel_local_file, s3_file)
        self.assertIn(output_str, self.output.getvalue())

    def test_run_ls(self):
        """
        This ensures that the architecture sets up correctly for a ``ls``
        command.  It is just just a dry run, but all of the components need
        to be wired correctly for it to work.
        """
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        s3_prefix = 's3://' + self.bucket + '/'
        params = {'dir_op': True, 'dryrun': True, 'quiet': False,
                  'src': s3_prefix, 'dest': s3_prefix, 'paths_type': 's3'}
        cmd_arc = CommandArchitecture(self.session, 'ls', params)
        cmd_arc.create_instructions()
        cmd_arc.run()

    def test_run_mb(self):
        """
        This ensures that the architecture sets up correctly for a ``rb``
        command.  It is just just a dry run, but all of the components need
        to be wired correctly for it to work.
        """
        s3_prefix = 's3://' + self.bucket + '/'
        params = {'dir_op': True, 'dryrun': True, 'quiet': False,
                  'src': s3_prefix, 'dest': s3_prefix, 'paths_type': 's3'}
        cmd_arc = CommandArchitecture(self.session, 'mb', params)
        cmd_arc.create_instructions()
        cmd_arc.run()
        output_str = "(dryrun) make_bucket: %s" % s3_prefix[5:-1]
        self.assertIn(output_str, self.output.getvalue())

    def test_run_rb(self):
        """
        This ensures that the architecture sets up correctly for a ``mb``
        command.  It is just just a dry run, but all of the components need
        to be wired correctly for it to work.
        """
        s3_prefix = 's3://' + self.bucket + '/'
        params = {'dir_op': True, 'dryrun': True, 'quiet': False,
                  'src': s3_prefix, 'dest': s3_prefix, 'paths_type': 's3'}
        cmd_arc = CommandArchitecture(self.session, 'rb', params)
        cmd_arc.create_instructions()
        cmd_arc.run()
        output_str = "(dryrun) remove_bucket: %s" % s3_prefix[5:-1]
        self.assertIn(output_str, self.output.getvalue())


class CommandParametersTest(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession()
        self.mock = MagicMock()
        self.mock.get_config = MagicMock(return_value={'region': None})
        self.loc_files = make_loc_files()
        self.bucket = make_s3_files(self.session)

    def tearDown(self):
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket, self.session)

    def test_add_paths(self):
        """
        This ensures that the paths are assigned properly in the
        class's parameters dictionary.
        """
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        path1 = [s3_file, 's3://some_file']
        path2 = [s3_file]
        cmd_params = CommandParameters(self.session, 'cp', {})
        cmd_params2 = CommandParameters(self.session, 'rm', {})
        cmd_params.check_region([])
        cmd_params2.check_region([])
        cmd_params.add_paths(path1)
        cmd_params2.add_paths(path2)
        ref_params = {'dir_op': False, 'src': s3_file,
                      'dest': 's3://some_file',
                      'region': self.session.get_config()['region'],
                      'paths_type': 's3s3'}
        self.assertEqual(cmd_params.parameters, ref_params)
        ref_params2 = {'dir_op': False, 'src': s3_file, 'dest': s3_file,
                       'region': self.session.get_config()['region'],
                       'paths_type': 's3'}
        self.assertEqual(cmd_params2.parameters, ref_params2)

    def test_check_path_type_pass(self):
        """
        This tests the class's ability to determine whether the correct
        path types have been passed for a particular command.  It test every
        possible combination that is correct for every command.
        """
        cmds = {'cp': ['locals3', 's3s3', 's3local'],
                'mv': ['locals3', 's3s3', 's3local'],
                'rm': ['s3'], 'ls': ['s3'], 'mb': ['s3'], 'rb': ['s3'],
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
            cmd_param = CommandParameters(self.session, cmd, {})
            cmd_param.check_region([])
            correct_paths = cmds[cmd]
            for path_args in correct_paths:
                cmd_param.check_path_type(combos[path_args])

    def test_check_path_type_fail(self):
        """
        This tests the class's ability to determine whether the correct
        path types have been passed for a particular command. It test every
        possible combination that is incorrect for every command.
        """

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
            cmd_param = CommandParameters(self.session, cmd, {})
            cmd_param.check_region([])
            wrong_paths = cmds[cmd]
            for path_args in wrong_paths:
                with self.assertRaises(TypeError):
                    cmd_param.check_path_type(combos[path_args])

    def test_check_src_path_pass(self):
        """
        This tests to see if all of the checks on the source path works.  It
        does so by testing if s3 objects and and prefixes exist as well as
        local files and directories.  All of these should not throw an
        exception.
        """
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        local_file = self.loc_files[0]
        s3_prefix = 's3://' + self.bucket
        local_dir = self.loc_files[3]

        # :var files: a list of tuples where the first element is a single
        #     element list of file paths. The second element is a boolean
        #     representing if the operation is a directory operation.
        files = [([s3_file], False), ([local_file], False),
                 ([s3_prefix], True), ([local_dir], True)]

        parameters = {}
        for filename in files:
            parameters['dir_op'] = filename[1]
            cmd_parameter = CommandParameters(self.session, 'put', parameters)
            cmd_parameter.check_region([])
            cmd_parameter.check_src_path(filename[0])

    def test_check_src_path_fail(self):
        """
        This tests to see if all of the checks on the source path works.  It
        does so by testing if s3 objects and and prefixes do not exist as well
        as local files and directories.  All of these should throw an
        exception.
        """
        local_file = self.loc_files[0]
        local_dir = self.loc_files[3]
        fake_s3_file = 's3://' + self.bucket + '/' + 'text1.tx'
        fake_local_file = local_file[:-1]
        fake_s3_prefix = 's3://' + self.bucket + '/' + 'fake/'
        fake_local_dir = local_dir + os.sep + 'fake' + os.sep

        # :var files: a list of tuples where the first element is a single
        #     element list of file paths. The second element is a boolean
        #     representing if the operation is a directory operation.
        files = [([fake_s3_file], False), ([fake_local_file], False),
                 ([fake_s3_prefix], True), ([local_file], True),
                 ([local_dir], False), ([fake_s3_file+'dag'], False)]

        parameters = {}
        for filename in files:
            parameters['dir_op'] = filename[1]
            cmd_parameter = CommandParameters(self.session, 'put', parameters)
            cmd_parameter.check_region([])
            with self.assertRaises(Exception):
                cmd_parameter.check_src_path(filename[0])

    def test_check_force(self):
        """
        This checks to make sure that the force parameter is run. If
        successful. The delete command will fail as the bucket is empty
        and be caught by the exception.
        """
        cmd_params = CommandParameters(self.session, 'rb', {'force': True})
        cmd_params.parameters['src'] = 's3://mybucket'
        cmd_params.check_force(None, None)

    def test_region(self):
        """
        This tests the ability to specify the region and throw an error
        if a region is never specified whether if it is an environment
        variable, config file, or parsed global.
        """
        cmd_params = CommandParameters(self.session, 'mb', {})
        parser = argparse.ArgumentParser()
        parser.add_argument('--region', nargs=1)
        parser.add_argument('--test', action='store_true')
        parsed_args = parser.parse_args(['--region', 'eu-west-1'])
        cmd_params.check_region(parsed_args)
        self.assertEqual(cmd_params.parameters['region'][0], 'eu-west-1')

        cmd_params2 = CommandParameters(self.mock, 'mb', {})
        parsed_args2 = parser.parse_args(['--test'])
        with self.assertRaises(Exception):
            cmd_params2.check_region(parsed_args2)


class HelpDocTest(BaseAWSHelpOutput):
    def setUp(self):
        super(HelpDocTest, self).setUp()
        self.session = botocore.session.get_session()

    def tearDown(self):
        super(HelpDocTest, self).tearDown()

    def test_s3_help(self):
        """
        This tests the help command for the s3 service. This
        checks to make sure the appropriate descriptions are
        added including the tutorial.
        """
        s3 = S3('s3', self.session)
        parser = argparse.ArgumentParser()
        parser.add_argument('--paginate', action='store_true')
        parsed_global = parser.parse_args(['--paginate'])
        help_command = s3.create_help_command()
        help_command([], parsed_global)
        self.assert_contains("This provides higher level S3 commands")
        self.assert_contains("Every command takes one or two positional")
        self.assert_contains("* rb")

    def test_s3command_help(self):
        """
        This tests the help command for an s3 command. This
        checks to make sure the command prints appropriate
        parts.  Note the examples are not included because
        the event was not registered.
        """
        s3command = S3Command('cp', self.session, {'nargs': 2})
        parser = argparse.ArgumentParser()
        parser.add_argument('--paginate', action='store_true')
        parsed_global = parser.parse_args(['--paginate'])
        help_command = s3command.create_help_command()
        help_command([], parsed_global)
        self.assert_contains("cp")
        self.assert_contains("[--acl <value>]")
        self.assert_contains("Displays the operations that would be")

    def test_help(self):
        """
        This ensures that the file appropriately redirects to help object
        if help is the only argument left to be parsed.  There should not
        have any contents in the docs.
        """
        s3_command = S3Command('sync', self.session, {'nargs': 2})
        s3_command(['help'], [])
        self.assert_contains('sync')
        self.assert_contains("Synopsis")

if __name__ == "__main__":
    unittest.main()
