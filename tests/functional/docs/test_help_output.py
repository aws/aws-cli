#!/usr/bin/env python
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
"""Test help output for the AWS CLI.

The purpose of these docs is to test that the generated output looks how
we expect.

It's intended to be as end to end as possible, but instead of looking
at the man output, we look one step before at the generated rst output
(it's easier to verify).

"""
from awscli.testutils import BaseAWSHelpOutputTest
from awscli.testutils import FileCreator
from awscli.testutils import mock
from awscli.testutils import aws
from awscli.compat import StringIO

from awscli.alias import AliasLoader


class TestHelpOutput(BaseAWSHelpOutputTest):
    def test_output(self):
        self.driver.main(['help'])
        # Check for the reference label.
        self.assert_contains('.. _cli:aws:')
        self.assert_contains('***\naws\n***')
        self.assert_contains(
            'The AWS Command Line Interface is a unified tool '
            'to manage your AWS services.')
        self.assert_contains('Use *aws help topics* to view')
        # Verify we see the docs for top level params, so pick
        # a few representative types of params.
        self.assert_contains('``--endpoint-url``')
        # Boolean type
        self.assert_contains('``--no-paginate``')
        # Arg with choices
        self.assert_contains('``--color``')
        self.assert_contains('*   on')
        self.assert_contains('*   off')
        self.assert_contains('*   auto')
        # Then we should see the services.
        self.assert_contains('* ec2')
        self.assert_contains('* s3api')
        self.assert_contains('* sts')
        # Make sure it its a related item
        self.assert_contains('========\nSee Also\n========')
        self.assert_contains('aws help topics')

    def test_service_help_output(self):
        self.driver.main(['ec2', 'help'])
        # Check for the reference label.
        self.assert_contains('.. _cli:aws ec2:')
        # We should see the section title for the service.
        self.assert_contains('***\nec2\n***')
        # With a description header.
        self.assert_contains('===========\nDescription\n===========')
        # And we should see the operations listed.
        self.assert_contains('* monitor-instances')
        self.assert_contains('* run-instances')
        self.assert_contains('* describe-instances')

    def test_operation_help_output(self):
        self.driver.main(['ec2', 'run-instances', 'help'])
        # Check for the reference label.
        self.assert_contains('.. _cli:aws ec2 run-instances:')
        # Should see the title with the operation name
        self.assert_contains('*************\nrun-instances\n*************')
        # Should contain part of the help text from the model.
        self.assert_contains('Launches the specified number of instances')
        self.assert_contains('``--count`` (string)')

    def test_custom_service_help_output(self):
        self.driver.main(['s3', 'help'])
        self.assert_contains('.. _cli:aws s3:')
        self.assert_contains('high-level S3 commands')
        self.assert_contains('* cp')

    def test_waiter_does_not_have_global_args(self):
        self.driver.main(['ec2', 'wait', 'help'])
        self.assert_not_contains('--debug')
        self.assert_not_contains('Global Options')

    def test_custom_operation_help_output(self):
        self.driver.main(['s3', 'ls', 'help'])
        self.assert_contains('.. _cli:aws s3 ls:')
        self.assert_contains('List S3 objects')
        self.assert_contains('--summarize')
        self.assert_contains('--debug')

    def test_topic_list_help_output(self):
        self.driver.main(['help', 'topics'])
        # Should contain the title
        self.assert_contains(
            '*******************\nAWS CLI Topic Guide\n*******************'
        )
        # Should contain the description
        self.assert_contains('This is the AWS CLI Topic Guide.')
        # Should contain the available topics section
        self.assert_contains('Available Topics')
        # Assert the general order of topic categories.
        self.assert_text_order(
            '-------\nGeneral\n-------',
            '--\nS3\n--',
            starting_from='Available Topics'
        )
        # Make sure that the topic elements elements show up as well.
        self.assert_contains(
            '* return-codes: Describes'
        )
        # Make sure the topic elements are underneath the categories as well
        # and they get added to each category they fall beneath
        self.assert_text_order(
            '-------\nGeneral\n-------',
            '* return-codes: Describes',
            '--\nS3\n--',
            starting_from='-------\nGeneral\n-------'
        )

    def test_topic_help_command(self):
        self.driver.main(['help', 'return-codes'])
        self.assert_contains(
            '********************\nAWS CLI Return Codes\n********************'
        )
        self.assert_contains('These are the following return codes')

    def test_arguments_with_example_json_syntax(self):
        self.driver.main(['ec2', 'run-instances', 'help'])
        self.assert_contains('``--iam-instance-profile``')
        self.assert_contains('JSON Syntax')
        self.assert_contains('"Arn": "string"')
        self.assert_contains('"Name": "string"')

    def test_arguments_with_example_shorthand_syntax(self):
        self.driver.main(['ec2', 'run-instances', 'help'])
        self.assert_contains('``--iam-instance-profile``')
        self.assert_contains('Shorthand Syntax')
        self.assert_contains('Arn=string,Name=string')

    def test_required_args_come_before_optional_args(self):
        self.driver.main(['ec2', 'run-instances', 'help'])
        # We're asserting that the args in the synopsis section appear
        # in this order.  They don't have to be in this exact order, but
        # each item in the list has to come before the previous arg.
        self.assert_text_order(
            '--image-id <value>',
            '[--key-name <value>]',
            '[--security-groups <value>]', starting_from='Synopsis')

    def test_service_operation_order(self):
        self.driver.main(['ec2', 'help'])
        self.assert_text_order(
            'activate-license',
            'allocate-address',
            'assign-private-ip-addresses', starting_from='Available Commands')

    def test_top_level_args_order(self):
        self.driver.main(['help'])
        self.assert_text_order(
            'autoscaling\n', 'cloudformation\n', 'elb\n', 'swf\n',
            starting_from='Available Services')

    def test_examples_in_operation_help(self):
        self.driver.main(['ec2', 'run-instances', 'help'])
        self.assert_contains('========\nExamples\n========')

    def test_add_help_for_dryrun(self):
        self.driver.main(['ec2', 'run-instances', 'help'])
        self.assert_contains('DryRunOperation')
        self.assert_contains('UnauthorizedOperation')

    def test_elb_help_output(self):
        self.driver.main(['elb', 'help'])
        # We should *not* have any invalid links like
        # .. _`:
        self.assert_not_contains('.. _`:')

    def test_shorthand_flattens_list_of_single_member_structures(self):
        self.driver.main(['elb', 'remove-tags', 'help'])
        self.assert_contains("--tags Key1 Key2 Key3")

    def test_deprecated_operations_not_documented(self):
        self.driver.main(['s3api', 'help'])
        self.assert_not_contains('get-bucket-lifecycle\n')
        self.assert_not_contains('put-bucket-lifecycle\n')
        self.assert_not_contains('get-bucket-notification\n')
        self.assert_not_contains('put-bucket-notification\n')


class TestRemoveDeprecatedCommands(BaseAWSHelpOutputTest):
    def assert_command_does_not_exist(self, service, command):
        # Basically try to get the help output for the removed
        # command verify that we get a SystemExit exception
        # and that we get something in stderr that says that
        # we made an invalid choice (because the operation is removed).
        stderr = StringIO()
        with mock.patch('sys.stderr', stderr):
            with self.assertRaises(SystemExit):
                self.driver.main([service, command, 'help'])
        # We should see an error message complaining about
        # an invalid choice because the operation has been removed.
        self.assertIn('argument operation: Invalid choice', stderr.getvalue())

    def test_ses_deprecated_commands(self):
        self.driver.main(['ses', 'help'])
        self.assert_not_contains('list-verified-email-addresses')
        self.assert_not_contains('delete-verified-email-address')
        self.assert_not_contains('verify-email-address')

        self.assert_command_does_not_exist(
            'ses', 'list-verified-email-addresses')
        self.assert_command_does_not_exist(
            'ses', 'delete-verified-email-address')
        self.assert_command_does_not_exist(
            'ses', 'verify-email-address')

    def test_ec2_import_export(self):
        self.driver.main(['ec2', 'help'])
        self.assert_not_contains('import-instance')
        self.assert_not_contains('import-volume')
        self.assert_command_does_not_exist(
            'ec2', 'import-instance')
        self.assert_command_does_not_exist(
            'ec2', 'import-volume')

    def test_boolean_param_documented(self):
        self.driver.main(['autoscaling',
                          'terminate-instance-in-auto-scaling-group', 'help'])
        self.assert_contains(
            ('``--should-decrement-desired-capacity`` | '
             '``--no-should-decrement-desired-capacity`` (boolean)'))

    def test_streaming_output_arg(self):
        self.driver.main(['s3api', 'get-object', 'help'])
        self.assert_not_contains('``--outfile``')
        self.assert_contains('``outfile`` (string)')

    def test_rds_add_arg_help_has_correct_command_name(self):
        self.driver.main(['rds', 'add-option-to-option-group', 'help'])
        self.assert_contains('add-option-to-option-group')

    def test_rds_remove_arg_help_has_correct_command_name(self):
        self.driver.main(['rds', 'remove-option-from-option-group', 'help'])
        self.assert_contains('remove-option-from-option-group')

    def test_modify_operation_not_in_help(self):
        self.driver.main(['rds', 'help'])
        # This was split into add/remove commands.  The modify
        # command should not be available.
        self.assert_not_contains('modify-option-group')


class TestPagingParamDocs(BaseAWSHelpOutputTest):
    def test_starting_token_injected(self):
        self.driver.main(['s3api', 'list-objects', 'help'])
        self.assert_contains('``--starting-token``')

    def test_max_items_injected(self):
        self.driver.main(['s3api', 'list-objects', 'help'])
        self.assert_contains('``--max-items``')

    def test_builtin_paging_params_removed(self):
        self.driver.main(['s3api', 'list-objects', 'help'])
        self.assert_not_contains('``--next-token``')
        self.assert_not_contains('``--max-keys``')

    def test_paging_documentation_added(self):
        self.driver.main(['s3api', 'list-objects', 'help'])
        self.assert_contains('``list-objects`` is a paginated operation')
        self.assert_contains('When using ``--output text`` and the')
        self.assert_contains('following query expressions: ')


class TestMergeBooleanGroupArgs(BaseAWSHelpOutputTest):
    def test_merge_bool_args(self):
        # Boolean args need to be group together so rather than
        # --foo foo docs
        # --no-foo foo docs again
        #
        # We instead have:
        # --foo | --no-foo foo docs
        self.driver.main(['ec2', 'run-instances', 'help'])
        self.assert_contains('``--dry-run`` | ``--no-dry-run``')

    def test_top_level_bools(self):
        # structure(scalar) of a single value of Value whose value is
        # a boolean is pulled into a top level arg.
        self.driver.main(['ec2', 'modify-instance-attribute', 'help'])
        self.assert_contains('``--ebs-optimized`` | ``--no-ebs-optimized``')

    def test_top_level_bool_has_no_example(self):
        # Normally a structure(bool) param would have an example
        # of {"Value": true|false}", but when we pull the arg up into
        # a top level bool, we should not generate an example.
        self.driver.main(['ec2', 'modify-instance-attribute', 'help'])
        self.assert_not_contains('"Value": true|false')


class TestStructureScalarHasNoExamples(BaseAWSHelpOutputTest):
    def test_no_examples_for_structure_single_scalar(self):
        self.driver.main(['ec2', 'modify-instance-attribute', 'help'])
        self.assert_not_contains('"Value": "string"')
        self.assert_not_contains('Value=string')

    def test_example_for_single_structure_not_named_value(self):
        # Verify that if a structure does match our special case
        # (single element named "Value"), then we still document
        # the example syntax.
        self.driver.main(['s3api', 'create-bucket', 'help'])
        self.assert_contains('LocationConstraint=string')
        # Also should see the JSON syntax in the help output.
        self.assert_contains('"LocationConstraint": ')


class TestJSONListScalarDocs(BaseAWSHelpOutputTest):
    def test_space_separated_list_docs(self):
        # A list of scalar type can be specified as JSON:
        #      JSON Syntax:
        #
        #       ["string", ...]
        # But at the same time you can always replace that with
        # a space separated list.  Therefore we want to document
        # the space separated list version and not the JSON list
        # version.
        self.driver.main(['ec2', 'terminate-instances', 'help'])
        self.assert_not_contains('["string", ...]')
        self.assert_contains('"string" "string"')


class TestParamRename(BaseAWSHelpOutputTest):
    def test_create_image_renames(self):
        # We're just cherry picking this particular operation to verify
        # that the rename arg customizations are working.
        self.driver.main(['ec2', 'create-image', 'help'])
        self.assert_not_contains('no-no-reboot')
        self.assert_contains('--reboot')

class TestCustomCommandDocsFromFile(BaseAWSHelpOutputTest):
    def test_description_from_rst_file(self):
        # The description for the configure command
        # is in _description.rst.  We're verifying that we
        # can read those contents properly.
        self.driver.main(['configure', 'help'])
        # These are a few options that are documented in the help output.
        self.assert_contains('metadata_service_timeout')
        self.assert_contains('metadata_service_num_attempts')
        self.assert_contains('aws_access_key_id')

class TestEnumDocsArentDuplicated(BaseAWSHelpOutputTest):
    def test_enum_docs_arent_duplicated(self):
        # Test for: https://github.com/aws/aws-cli/issues/609
        # What's happening is if you have a list param that has
        # an enum, we document it as:
        # a|b|c|d   a|b|c|d
        # Except we show all of the possible enum params twice.
        # Each enum param should only occur once.  The ideal documentation
        # should be:
        #
        # string1 string2
        #
        # Where each value is one of:
        #     value1
        #     value2
        self.driver.main(['cloudformation', 'list-stacks', 'help'])
        # "CREATE_IN_PROGRESS" is a enum value, and should only
        # appear once in the help output.
        contents = self.renderer.rendered_contents
        self.assertTrue(contents.count("CREATE_IN_PROGRESS") == 1,
                        ("Enum param was only suppose to be appear once in "
                         "rendered doc output, appeared: %s" %
                         contents.count("CREATE_IN_PROGRESS")))


class TestParametersCanBeHidden(BaseAWSHelpOutputTest):
    def mark_as_undocumented(self, argument_table, **kwargs):
        argument_table['starting-sequence-number']._UNDOCUMENTED = True

    def test_hidden_params_are_not_documented(self):
        # We're going to demonstrate hiding a parameter.
        # --device
        self.driver.session.register('building-argument-table',
                                     self.mark_as_undocumented)
        self.driver.main(['kinesis', 'get-shard-iterator', 'help'])
        self.assert_not_contains('--starting-sequence-number')


class TestCanDocumentAsRequired(BaseAWSHelpOutputTest):
    def test_can_doc_as_required(self):
        # This param is already marked as required, but to be
        # explicit this is repeated here to make it more clear.
        def doc_as_required(argument_table, **kwargs):
            arg = argument_table['volume-arns']
        self.driver.session.register('building-argument-table',
                                     doc_as_required)
        self.driver.main(['storagegateway', 'describe-cached-iscsi-volumes',
                          'help'])
        self.assert_not_contains('[--volume-arns <value>]')


class TestEC2AuthorizeSecurityGroupNotRendered(BaseAWSHelpOutputTest):
    def test_deprecated_args_not_documented(self):
        self.driver.main(['ec2', 'authorize-security-group-ingress', 'help'])
        self.assert_not_contains('--ip-protocol')
        self.assert_not_contains('--from-port')
        self.assert_not_contains('--to-port')
        self.assert_not_contains('--source-security-group-name')
        self.assert_not_contains('--source-security-group-owner-id')


class TestKMSCreateGrant(BaseAWSHelpOutputTest):
    def test_proper_casing(self):
        self.driver.main(['kms', 'create-grant', 'help'])
        # Ensure that the proper casing is used for this command's docs.
        self.assert_not_contains('generate-data-key')
        self.assert_contains('GenerateDataKey')


class TestRoute53CreateHostedZone(BaseAWSHelpOutputTest):
    def test_proper_casing(self):
        self.driver.main(['route53', 'create-hosted-zone', 'help'])
        # Ensure that the proper casing is used for this command's docs.
        self.assert_contains(
            'do **not** include ``PrivateZone`` in this input structure')


class TestIotData(BaseAWSHelpOutputTest):
    def test_service_help_command_has_note(self):
        self.driver.main(['iot-data', 'help'])
        # Ensure the note is in help page.
        self.assert_contains(
            'The default endpoints (intended for testing purposes only) can be found at '
            'https://docs.aws.amazon.com/general/latest/gr/iot-core.html#iot-core-data-plane-endpoints')

    def test_operation_help_command_has_note(self):
        self.driver.main(['iot-data', 'get-thing-shadow', 'help'])
        # Ensure the note is in help page.
        self.assert_contains(
            'The default endpoints (intended for testing purposes only) can be found at '
            'https://docs.aws.amazon.com/general/latest/gr/iot-core.html#iot-core-data-plane-endpoints')


class TestSMSVoice(BaseAWSHelpOutputTest):
    def test_service_help_not_listed(self):
        self.driver.main(['help'])
        # Ensure the hidden service is not in the help listing.
        self.assert_not_contains('* sms-voice')


class TestAliases(BaseAWSHelpOutputTest):
    def setUp(self):
        super(TestAliases, self).setUp()
        self.files = FileCreator()
        self.alias_file = self.files.create_file('alias', '[toplevel]\n')
        self.driver.alias_loader = AliasLoader(self.alias_file)

    def tearDown(self):
        super(TestAliases, self).tearDown()
        self.files.remove_all()

    def add_alias(self, alias_name, alias_value):
        with open(self.alias_file, 'a+') as f:
            f.write('%s = %s\n' % (alias_name, alias_value))

    def test_alias_not_in_main_help(self):
        self.add_alias('my-alias', 'ec2 describe-regions')
        self.driver.main(['help'])
        self.assert_not_contains('my-alias')


class TestStreamingOutputHelp(BaseAWSHelpOutputTest):
    def test_service_help_command_has_note(self):
        self.driver.main(['s3api', 'get-object', 'help'])
        self.assert_not_contains('outfile <value>')
        self.assert_contains('<outfile>')


# Use this test class for "help" cases that require the default renderer
# (i.e. renderer from get_render()) instead of a mocked version.
class TestHelpOutputDefaultRenderer:
    def test_line_lengths_do_not_break_create_launch_template_version_cmd(self):
        result = aws('ec2 create-launch-template-version help')
        assert 'exceeds the line-length-limit' not in result.stderr
