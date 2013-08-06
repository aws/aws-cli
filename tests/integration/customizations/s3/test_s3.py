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
import os
import argparse
import awscli
import sys
import botocore.session

from mock import Mock, MagicMock
from awscli.customizations.s3.s3 import AppendFilter, cmd_dict, \
    params_dict, awscli_initialize, add_s3, add_commands, add_cmd_params, \
    S3, S3Command, S3Parameter, CommandArchitecture, CommandParameters
from tests.integration.customizations.s3.test_filegenerator import \
    make_loc_files, clean_loc_files, make_s3_files, s3_cleanup, create_bucket

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

"""
Note that all of these functions can be found in the unit tests.
The only difference is that these tests use botocore's actual session
variables to communicate with s3 as these are integration tests.  Therefore,
only tests that use sessions are included as integration tests.
"""


class S3Test(unittest.TestCase):
    """
    This test to ensure the command object can be called from
    parsing a command in the service object
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
    This checks top make sure that the S3Command class works.  If successful,
    it will print out the buckets that is owned.  It essentially checks that
    the class works along with all of the objects used to complete the
    command.  The test_help enusres a command's help can be displayed
    when inputted to the command line
    """
    def test_call(self):
        session = botocore.session.get_session()
        s3_command = S3Command('ls', session, 1)
        s3_command(['s3://'], [])

    def test_help(self):
        session = botocore.session.get_session()
        s3_command = S3Command('ls', session, 1)
        with self.assertRaises(SystemExit):
            s3_command(['help'], [])


class CommandArchitectureTest(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.bucket = make_s3_files()
        self.loc_files = make_loc_files()

    def tearDown(self):
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket)

    def test_create_instructions(self):
        """
        This tests to make sure the instructions for any command is generated
        properly
        """
        cmds = ['put', 'get', 'copy', 'mv', 'rm',
                'sync', 'ls', 'mb', 'rb']

        instructions = {'put': ['file_generator', 's3_handler'],
                        'get': ['file_generator', 's3_handler'],
                        'copy': ['file_generator', 's3_handler'],
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

        #test if there is a filter
        cmd_arc = CommandArchitecture(self.session, 'put', params)
        cmd_arc.create_instructions()
        self.assertEqual(cmd_arc.instructions, ['file_generator', 'filters',
                                                's3_handler'])

    def test_run(self):
        """
        This ensures that the architecture sets up correctly.  It is really
        just a dry run, but all of the components need to be wired correctly
        for it to work.  If they are not wired properly this test will fail.
        It tests every possible component for a specified command.  Note
        nothing is ever operated on because every command is dryrunned.
        """
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        local_file = self.loc_files[0]
        s3_prefix = 's3://' + self.bucket + '/'
        local_dir = self.loc_files[3]

        cmds = ['put', 'get', 'copy', 'mv', 'rm',
                'sync', 'ls', 'mb', 'rb']

        path_dict = {'put': {'src': local_file, 'dest': s3_file},
                     'get': {'src': s3_file, 'dest': local_file},
                     'copy': {'src': s3_file, 'dest': s3_file},
                     'mv': {'src': s3_file, 'dest': s3_file},
                     'rm': {'src': s3_file, 'dest': s3_file},
                     'sync': {'src': local_dir, 'dest': s3_prefix},
                     'ls': {'src': s3_prefix, 'dest': s3_prefix},
                     'mb': {'src': s3_prefix, 'dest': s3_prefix},
                     'rb': {'src': s3_prefix, 'dest': s3_prefix}}

        filters = [['--include', '*']]

        for cmd in cmds:
            params = {'dir_op': False, 'dryrun': True, 'quiet': True,
                      'src': path_dict[cmd]['src'],
                      'dest': path_dict[cmd]['dest'],
                      'filters': None}
            if cmd in ['sync', 'ls', 'mb', 'rb']:
                params['dir_op'] = True
            else:
                params['dir_op'] = False
            if cmd in ['put', 'get', 'copy', 'mv', 'rm', 'sync']:
                params['filters'] = filters
            else:
                params['filters'] = None
            cmd_arc = CommandArchitecture(self.session, cmd, params)
            cmd_arc.create_instructions()
            cmd_arc.run()


class CommandParametersTest(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()
        self.mock = MagicMock()
        self.mock.get_config = MagicMock(return_value={'region': None})
        self.loc_files = make_loc_files()
        self.bucket = make_s3_files()

    def tearDown(self):
        clean_loc_files(self.loc_files)
        s3_cleanup(self.bucket)

    def test_add_paths(self):
        """
        This ensures that the paths are assigned properly in the
        class's parameters dictionary
        """
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        path1 = [s3_file, 's3://some_file']
        path2 = [s3_file]
        cmd_params = CommandParameters(self.session, 'copy', {})
        cmd_params2 = CommandParameters(self.session, 'rm', {})
        cmd_params.check_region([])
        cmd_params2.check_region([])
        cmd_params.add_paths(path1)
        cmd_params2.add_paths(path2)
        ref_params = {'dir_op': False, 'src': s3_file,
                      'dest': 's3://some_file',
                      'region': self.session.get_config()['region']}
        self.assertEqual(cmd_params.parameters, ref_params)
        ref_params2 = {'dir_op': False, 'src': s3_file, 'dest': s3_file,
                       'region': self.session.get_config()['region']}
        self.assertEqual(cmd_params2.parameters, ref_params2)

    def test_check_path_type(self):
        """
        This tests the class's ability to determine whether the correct
        path types have been passed for a particular command.  It test every
        possible combination and every command.
        """

        cmds = ['put', 'get', 'copy', 'mv', 'rm',
                'sync', 'ls', 'mb', 'rb']
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        local_file = self.loc_files[0]

        combos = {'s3s3': [s3_file, s3_file],
                  's3local': [s3_file, local_file],
                  'locals3': [local_file, s3_file],
                  's3': [s3_file],
                  'local': [local_file],
                  'locallocal': [local_file, local_file]}

        template_type = {'s3s3': ['copy', 'sync', 'mv'],
                         's3local': ['get', 'sync'],
                         'locals3': ['put', 'sync'],
                         's3': ['ls', 'mb', 'rb', 'rm']}

        for cmd in cmds:
            cmd_param = CommandParameters(self.session, cmd, {})
            cmd_param.check_region([])
            for combo in combos.keys():
                if combo in template_type and cmd in template_type[combo]:
                    cmd_param.check_path_type(combos[combo])
                else:
                    with self.assertRaises(TypeError):
                        cmd_param.check_path_type(combos[combo])

    def test_check_src_path(self):
        """
        This tests to see if all of the checks on the source path works.  It
        does so by testing if s3 objects and and prefixes exist.  If file and
        directories exist.  If a directory operation is being used on a
        file and vice versa.
        :var files: a list of tuples where the first element is a single
            element list of file paths. The second element is a boolean
            representing if the operation is a directory operation.  The
            third element represents whether an exception will be raised.
        """
        s3_file = 's3://' + self.bucket + '/' + 'text1.txt'
        fake_s3_file = s3_file[:-1]

        local_file = self.loc_files[0]
        fake_local_file = local_file[:-1]

        s3_prefix = 's3://' + self.bucket
        fake_s3_prefix = s3_prefix + '/' + 'fake/'

        local_dir = self.loc_files[3]
        fake_local_dir = local_dir + os.sep + 'fake' + os.sep

        files = [([s3_file], False, False), ([fake_s3_file], False, True),
                 ([local_file], False, False), ([fake_local_file], False,
                                                True),
                 ([s3_prefix], True, False), ([fake_s3_prefix], True, True),
                 ([local_dir], True, False), ([local_file], True, True),
                 ([local_dir], False, True)]

        parameters = {}
        for filename in files:
            parameters['dir_op'] = filename[1]
            cmd_parameter = CommandParameters(self.session, 'put', parameters)
            cmd_parameter.check_region([])
            if filename[2]:
                with self.assertRaises(Exception):
                    cmd_parameter.check_src_path(filename[0])
            else:
                cmd_parameter.check_src_path(filename[0])

    def test_check_force(self):
        """
        This checks to make sure that the force parameter is run. If
        successful. The delete command will fail as the bucket is empty
        and be caught by the exception
        """
        cmd_params = CommandParameters(self.session, 'mb', {'force': True})
        cmd_params.parameters['src'] = 's3://mybucket'
        cmd_params.check_force(None, None)

    def test_region(self):
        """
        This tests the ability to specify the region and throw an error
        if a region is never specified whether if it is an environment
        variable, config file, or parsed global
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


class HelpDocTest(unittest.TestCase):
    def setUp(self):
        self.session = botocore.session.get_session()

    def test_s3_help(self):
        """
        This tests the help command for the s3 service. The
        end result should print the help doc and will exit
        """
        s3 = S3('s3', self.session)
        parser = argparse.ArgumentParser()
        parser.add_argument('--paginate', action='store_true')
        parsed_global = parser.parse_args(['--paginate'])
        help_command = s3.create_help_command()
        with self.assertRaises(SystemExit):
            help_command([], parsed_global)

    def test_s3command_help(self):
        """
        This tests the help command for an s3 command. The
        end result should print the help doc and will exit
        """
        s3command = S3Command('put', self.session, 2)
        parser = argparse.ArgumentParser()
        parser.add_argument('--paginate', action='store_true')
        parsed_global = parser.parse_args(['--paginate'])
        help_command = s3command.create_help_command()
        with self.assertRaises(SystemExit):
            help_command([], parsed_global)


if __name__ == "__main__":
    unittest.main()
