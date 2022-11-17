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

from awscli.alias import AliasLoader, register_alias_commands
from awscli.testutils import skip_if_windows
from awscli.testutils import FileCreator
from awscli.testutils import BaseAWSCommandParamsTest
from awscli.customizations.commands import BasicCommand


# We need to test that aliases work with custom BasicCommand,
# but the actual custom commands in the CLI can be complex and 
# don't want the alias tests to fail if they are updated with new API
# calls they invoke.  This custom command is a simple wrapper to the
# aws resourcegroupstaggingapi get-resources command.
class CustomTestCommand(BasicCommand):
    NAME = 'resources'
    ARG_TABLE = [
        {'name': 'resource-types', 'action': 'store', 'required': False},
        {'name': 'tags', 'action': 'store', 'required': False},
    ]

    def _run_main(self, parsed_args, parsed_globals):
        client = self._session.create_client('resourcegroupstaggingapi')
        kwargs = {}
        if parsed_args.resource_types is not None:
            kwargs['ResourceTypeFilters'] = [parsed_args.resource_types]
        if parsed_args.tags is not None:
            key, value = parsed_args.tags.split('=')
            kwargs['TagFilters'] = [{'Key': key, 'Values': [value]}]
        client.get_resources(**kwargs)


class TestAliases(BaseAWSCommandParamsTest):
    def setUp(self):
        super(TestAliases, self).setUp()
        self.files = FileCreator()
        self.alias_file = self.files.create_file('alias', '[toplevel]\n')
        self.driver.alias_loader = AliasLoader(self.alias_file)
        self.event_emitter = self.driver.session.get_component('event_emitter')
        # Alias injection is part of the built-in handler chain which defaults
        # to the real ~/.aws/cli/alias file.  We need to unregister the default
        # injector so we can swap in our own version that points to a
        # test file.
        self.event_emitter.unregister(
            'building-command-table', unique_id='cli-alias-injector')
        register_alias_commands(
            self.event_emitter,
            alias_filename=self.alias_file
        )

    def tearDown(self):
        super(TestAliases, self).tearDown()
        self.files.remove_all()

    def add_alias(self, alias_name, alias_value):
        with open(self.alias_file, 'a+') as f:
            f.write('%s = %s\n' % (alias_name, alias_value))

    def assert_single_operation_called(self, cmdline,
                                       service_name, operation_name, params):
        self.assert_params_for_cmd(cmdline, params)
        operations_called = self.operations_called
        self.assertEqual(len(operations_called), 1)
        single_op = operations_called[0]
        self.assertEqual(
            single_op[0].service_model.service_name,
            service_name,
        )
        self.assertEqual(single_op[0].name, operation_name)

    def test_subcommand_alias(self):
        self.add_alias('my-alias', 'ec2 describe-regions')
        cmdline = 'my-alias'
        self.assert_params_for_cmd(cmdline, {})
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(
            self.operations_called[0][0].service_model.service_name,
            'ec2'
        )
        self.assertEqual(self.operations_called[0][0].name, 'DescribeRegions')

    def test_subcommand_alias_with_additonal_params(self):
        self.add_alias(
            'my-alias', 'ec2 describe-regions --region-names us-east-1')
        cmdline = 'my-alias'
        self.assert_params_for_cmd(cmdline, {'RegionNames': ['us-east-1']})
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(
            self.operations_called[0][0].service_model.service_name,
            'ec2'
        )
        self.assertEqual(self.operations_called[0][0].name, 'DescribeRegions')

    def test_subcommand_alias_then_additonal_params(self):
        self.add_alias('my-alias', 'ec2')
        cmdline = 'my-alias describe-regions --region-names us-east-1'
        self.assert_params_for_cmd(cmdline, {'RegionNames': ['us-east-1']})
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(
            self.operations_called[0][0].service_model.service_name,
            'ec2'
        )
        self.assertEqual(self.operations_called[0][0].name, 'DescribeRegions')

    def test_subcommand_alias_with_global_params(self):
        self.add_alias(
            'my-alias',
            'ec2 describe-regions --query Regions[].RegionName --output text')
        self.parsed_responses = [
            {
                'Regions': [
                    {
                        'Endpoint': 'ec2.us-east-1.amazonaws.com',
                        'RegionName': 'us-east-1'
                    }
                ]
            }
        ]
        cmdline = 'my-alias'
        stdout, _, _ = self.assert_params_for_cmd(cmdline, {})
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(
            self.operations_called[0][0].service_model.service_name,
            'ec2'
        )
        self.assertEqual(self.operations_called[0][0].name, 'DescribeRegions')
        self.assertEqual(stdout.strip(), 'us-east-1')

    def test_subcommand_alias_then_global_params(self):
        self.add_alias('my-alias', 'ec2 describe-regions')
        self.parsed_responses = [
            {
                'Regions': [
                    {
                        'Endpoint': 'ec2.us-east-1.amazonaws.com',
                        'RegionName': 'us-east-1'
                    }
                ]
            }
        ]
        cmdline = 'my-alias '
        cmdline += '--query=Regions[].RegionName '
        cmdline += '--output=text'
        stdout, _, _ = self.assert_params_for_cmd(cmdline, {})
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(
            self.operations_called[0][0].service_model.service_name,
            'ec2'
        )
        self.assertEqual(self.operations_called[0][0].name, 'DescribeRegions')
        self.assertEqual(stdout.strip(), 'us-east-1')

    def test_global_params_then_subcommand_alias(self):
        self.add_alias('my-alias', 'ec2 describe-regions')
        self.parsed_responses = [
            {
                'Regions': [
                    {
                        'Endpoint': 'ec2.us-east-1.amazonaws.com',
                        'RegionName': 'us-east-1'
                    }
                ]
            }
        ]
        cmdline = '--query=Regions[].RegionName '
        cmdline += '--output=text '
        cmdline += 'my-alias'
        stdout, _, _ = self.assert_params_for_cmd(cmdline, {})
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(
            self.operations_called[0][0].service_model.service_name,
            'ec2'
        )
        self.assertEqual(self.operations_called[0][0].name, 'DescribeRegions')
        self.assertEqual(stdout.strip(), 'us-east-1')

    def test_alias_overrides_builtin_command(self):
        self.add_alias('ec2', 's3api')
        cmdline = 'ec2 list-buckets'
        self.assert_params_for_cmd(cmdline, {})
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(self.operations_called[0][0].name, 'ListBuckets')

    def test_alias_proxies_to_shadowed_command(self):
        self.add_alias('ec2', 'ec2')
        cmdline = 'ec2 describe-regions'
        stdout, _, _ = self.assert_params_for_cmd(cmdline, {})
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(
            self.operations_called[0][0].service_model.service_name,
            'ec2'
        )
        self.assertEqual(self.operations_called[0][0].name, 'DescribeRegions')

    def test_alias_chaining(self):
        self.add_alias('base-alias', 'ec2 describe-regions')
        self.add_alias(
            'wrapper-alias', 'base-alias --region-names us-east-1')
        cmdline = 'wrapper-alias'
        self.assert_params_for_cmd(cmdline, {'RegionNames': ['us-east-1']})
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(
            self.operations_called[0][0].service_model.service_name,
            'ec2'
        )
        self.assertEqual(self.operations_called[0][0].name, 'DescribeRegions')

    def test_alias_chaining_with_globals(self):
        self.add_alias('base-alias', 'ec2 describe-regions')
        self.add_alias(
            'wrapper-alias',
            'base-alias --query Regions[].RegionName --output text')
        cmdline = 'wrapper-alias'
        self.parsed_responses = [
            {
                'Regions': [
                    {
                        'Endpoint': 'ec2.us-east-1.amazonaws.com',
                        'RegionName': 'us-east-1'
                    }
                ]
            }
        ]
        stdout, _, _ = self.assert_params_for_cmd(cmdline, {})
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(
            self.operations_called[0][0].service_model.service_name,
            'ec2'
        )
        self.assertEqual(self.operations_called[0][0].name, 'DescribeRegions')
        self.assertEqual(stdout.strip(), 'us-east-1')

    def test_external_alias(self):
        # The external alias is tested by using mkdir; a command that
        # is universal for the various OS's we support
        directory_to_make = os.path.join(self.files.rootdir, 'newdir')
        self.add_alias('mkdir', '!mkdir %s' % directory_to_make)
        self.run_cmd('mkdir')
        self.assertTrue(os.path.isdir(directory_to_make))

    def test_external_alias_then_additonal_args(self):
        # The external alias is tested by using mkdir; a command that
        # is universal for the various OS's we support
        directory_to_make = os.path.join(self.files.rootdir, 'newdir')
        self.add_alias('mkdir', '!mkdir')
        self.run_cmd('mkdir %s' % directory_to_make)
        self.assertTrue(os.path.isdir(directory_to_make))

    def test_external_alias_with_quoted_arguments(self):
        directory_to_make = os.path.join(self.files.rootdir, 'new dir')
        self.add_alias('mkdir', '!mkdir')
        self.run_cmd(['mkdir', directory_to_make])
        self.assertTrue(os.path.isdir(directory_to_make))

    @skip_if_windows('Windows does not support BASH functions')
    def test_external_alias_with_wrapper_bash_function(self):
        # The external alias is tested by using mkdir; a command that
        # is universal for the various OS's we support
        directory_to_make = os.path.join(self.files.rootdir, 'newdir')
        self.add_alias('mkdir', '!f() { mkdir "${1}"; }; f')
        self.run_cmd('mkdir %s' % directory_to_make)
        self.assertTrue(os.path.isdir(directory_to_make))

    def test_operation_level_alias_with_additonal_params(self):
        with open(self.alias_file, 'a+') as f:
            f.write('[command ec2]\n')
            f.write('regions = describe-regions --region-names us-west-2\n')

        cmdline = 'ec2 regions'
        self.assert_params_for_cmd(cmdline, {'RegionNames': ['us-west-2']})
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(
            self.operations_called[0][0].service_model.service_name,
            'ec2'
        )
        self.assertEqual(self.operations_called[0][0].name, 'DescribeRegions')

    def test_multi_nested_command_alias(self):
        with open(self.alias_file, 'a+') as f:
            f.write('[command ec2 wait]\n')
            f.write('vpc-ready = vpc-available\n')

        cmdline = 'ec2 wait vpc-ready'
        self.parsed_response = {
            'Vpcs': [{'State': 'available'}],
        }
        self.assert_params_for_cmd(cmdline)
        self.assertEqual(len(self.operations_called), 1)
        self.assertEqual(
            self.operations_called[0][0].service_model.service_name,
            'ec2'
        )
        self.assertEqual(self.operations_called[0][0].name, 'DescribeVpcs')

    def test_can_extend_subcommand_internal_aliases(self):
        with open(self.alias_file, 'a+') as f:
            f.write('[command ec2]\n')
            f.write('regions = describe-regions '
                    '--query Regions[].RegionName\n')
        cmdline = 'ec2 regions --region-names us-west-2'
        self.assert_single_operation_called(
            cmdline,
            service_name='ec2', operation_name='DescribeRegions',
            params={'RegionNames': ['us-west-2']})

    def test_operation_level_external_alias(self):
        directory_to_make = os.path.join(self.files.rootdir, 'newdir')
        with open(self.alias_file, 'a+') as f:
            f.write('[command ec2]\n')
            f.write('mkdir = !mkdir\n')
        self.run_cmd('ec2 mkdir %s' % directory_to_make)
        self.assertTrue(os.path.isdir(directory_to_make))

    def test_can_create_bag_of_options_alias(self):
        with open(self.alias_file, 'a+') as f:
            f.write('[command cloudformation list-stacks]\n')
            f.write('created = --stack-status-filter CREATE_COMPLETE '
                    '--query StackSummaries[].[StackName,StackStatus] '
                    '--output text\n')

        cmdline = 'cloudformation list-stacks created'
        self.assert_single_operation_called(
            cmdline,
            service_name='cloudformation',
            operation_name='ListStacks',
            params={'StackStatusFilter': ['CREATE_COMPLETE']},
        )

    def test_can_merge_explicit_and_alias_local_params(self):
        section = '[command resourcegroupstaggingapi get-resources]\n'
        alias = (
            'mysvc = --tag-filters Key=foo,Values=bar '
            'Key=bar,Values=baz --query ResourceTagMappingList[].[ResourceARN]'
            ' --output text\n'
        )
        with open(self.alias_file, 'a+') as f:
            f.write(section)
            f.write(alias)
        # If we add additional operatio-specific params such as
        # "--resource-type-filters ecs", then we should merge
        # those values with the params specified in the alias definition.
        self.run_cmd(
            'resourcegroupstaggingapi get-resources mysvc '
            '--resource-type-filters ecs')
        op_model, params = self.operations_called[0]
        self.assertEqual(op_model.name, 'GetResources')
        self.assertEqual(params, {
            'TagFilters': [
                {'Key': 'foo', 'Values': ['bar']},
                {'Key': 'bar', 'Values': ['baz']},
            ],
            'ResourceTypeFilters': ['ecs'],
        })

    def test_can_handle_bag_of_options_with_required_args(self):
        with open(self.alias_file, 'a+') as f:
            f.write('[command iam create-user]\n')
            f.write('test-user = --user-name test-user\n')
        # The current behavior without aliases is that `--user-name`
        # is a required parameter.  So without changing anything
        # if you ran "aws iam create-user test-user", the parser
        # would complain that the `--user-name` arg is required.
        # However, the `--user-name` is specified, it's just in the
        # `test-user` alias.  So we have to ensure that we're able
        # to delegate to the alias in the hopes that it can provide
        # the required value.  FWIW we had to do something similar
        # in the `--generate-cli-skeleton` flow.
        self.run_cmd('iam create-user test-user')
        op_model, params = self.operations_called[0]
        self.assertEqual(op_model.name, 'CreateUser')
        self.assertEqual(params, {
            'UserName': 'test-user',
        })

    def test_can_handle_bag_of_options_with_custom_command(self):
        self.event_emitter.register(
            'building-command-table.resourcegroupstaggingapi',
            CustomTestCommand.add_command)
        with open(self.alias_file, 'a+') as f:
            f.write('[command resourcegroupstaggingapi resources]\n')
            f.write(f'mycluster = --resource-types ecs:cluster\n')
        cmdline = 'resourcegroupstaggingapi resources mycluster'
        self.assert_single_operation_called(
            cmdline,
            service_name='resourcegroupstaggingapi',
            operation_name='GetResources',
            params={'ResourceTypeFilters': ['ecs:cluster']}
        )

    def test_can_handle_custom_bag_of_options_and_overrides(self):
        self.event_emitter.register(
            'building-command-table.resourcegroupstaggingapi',
            CustomTestCommand.add_command)
        with open(self.alias_file, 'a+') as f:
            f.write('[command resourcegroupstaggingapi resources]\n')
            f.write(f'mycluster = --resource-types ecs:cluster\n')
        cmdline = 'resourcegroupstaggingapi resources mycluster --tags foo=bar'
        # We should merge the cmdline params from the 'mycluster' alias along
        # with the explicitly provided --tags option from cmdline args.
        self.assert_single_operation_called(
            cmdline,
            service_name='resourcegroupstaggingapi',
            operation_name='GetResources',
            params={'ResourceTypeFilters': ['ecs:cluster'],
                    'TagFilters': [{'Key': 'foo', 'Values': ['bar']}]},
        )

    def test_can_invoke_custom_test_command(self):
        # Sanity check to ensure the custom test command we're using
        # works properly so we don't waste time debugging a test because
        # the test command implementation is wrong.
        self.event_emitter.register(
            'building-command-table.resourcegroupstaggingapi',
            CustomTestCommand.add_command)
        cmdline = 'resourcegroupstaggingapi resources --resource-types ecs --tags foo=bar'
        self.assert_single_operation_called(
            cmdline,
            service_name='resourcegroupstaggingapi',
            operation_name='GetResources',
            params={'ResourceTypeFilters': ['ecs'],
                    'TagFilters': [{'Key': 'foo', 'Values': ['bar']}]},
        )
