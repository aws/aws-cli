# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Functional tests for the ``--help`` parameter.

Cover ``--help`` on every command surface and confirm it renders the same help
as the ``help`` subcommand.
"""

from awscli.testutils import BaseAWSHelpOutputTest


class TestHelpFlagResolvedBeforeBinding(BaseAWSHelpOutputTest):
    """``--help`` renders help everywhere, before argument binding."""

    def test_help_flag_simple_operation(self):
        self.driver.main(['ec2', 'describe-instances', '--help'])
        self.assert_contains('describe-instances')

    def test_help_flag_provider(self):
        self.driver.main(['--help'])
        self.assert_contains('aws')

    def test_help_flag_service(self):
        self.driver.main(['ec2', '--help'])
        self.assert_contains('ec2')

    def test_help_flag_after_value_taking_option(self):
        # A space-separated value option precedes --help.  Resolving help before
        # binding shows the operation help rather than running the operation.
        self.driver.main(
            ['ec2', 'describe-instances', '--instance-ids', 'i-123', '--help']
        )
        self.assert_contains('describe-instances')

    def test_help_flag_before_value_taking_option(self):
        # --help before a value option still shows help, mirroring
        # `help --instance-ids i-123`.
        self.driver.main(
            ['ec2', 'describe-instances', '--help', '--instance-ids', 'i-123']
        )
        self.assert_contains('describe-instances')

    def test_help_flag_custom_command_positional(self):
        # `configure get <varname> --help`: the BasicCommand positional
        # `varname` consumes the real value, and --help still shows `get` help.
        self.driver.main(['configure', 'get', 'region', '--help'])
        self.assert_contains('get')

    def test_help_flag_optional_value_option(self):
        # `--generate-cli-skeleton --help`: an optional-value option precedes
        # --help, and the operation help still renders.
        self.driver.main(
            ['ec2', 'describe-instances', '--generate-cli-skeleton', '--help']
        )
        self.assert_contains('describe-instances')

    def test_abbreviation_is_not_help(self):
        # Exact-token-only: only the literal --help renders help.  An
        # abbreviation such as --hel is NOT help; it falls through to the
        # operation parser as an unknown option (exit 252, no help output).
        rc = self.driver.main(['ec2', 'describe-instances', '--hel'])
        self.assertEqual(rc, 252)
        self.assert_not_contains('describe-instances')

    def test_help_flag_waiter_state(self):
        self.driver.main(['ec2', 'wait', 'instance-running', '--help'])
        self.assert_contains('instance-running')

    def test_help_flag_custom_nested_command(self):
        self.driver.main(['cloudformation', 'package', '--help'])
        self.assert_contains('package')


class TestHelpFlagValueNotMisinterpreted(BaseAWSHelpOutputTest):
    """A genuine option *value* of ``--help`` must not trigger help."""

    def test_attached_value_help_is_not_help_request(self):
        # `--instance-ids=--help` supplies the string '--help' as the value of
        # --instance-ids; it is NOT a help request.  Help must NOT render
        # (the command proceeds and fails later on missing region/creds).
        rc = self.driver.main(
            ['ec2', 'describe-instances', '--instance-ids=--help']
        )
        self.assertNotEqual(rc, 0)
        self.assert_not_contains('describe-instances\n*****')


class TestHelpFlagPositionSelectsHelpLevel(BaseAWSHelpOutputTest):
    """Where ``--help`` sits selects which command level's help renders, since
    routing considers only the command tokens before the first ``--help``.
    Every token after ``--help`` is ignored.
    """

    def test_flag_before_operation_renders_service_help(self):
        # aws ec2 --help describe-instances ...  ==  aws ec2 help describe-instances ...
        # ``Available Commands`` appears in service and provider help but not in
        # operation help, so it marks that service help rendered here.
        self.driver.main(
            ['ec2', '--help', 'describe-instances', '--instance-ids', 'i-123']
        )
        self.assert_contains('Available Commands')  # service help

    def test_flag_after_operation_renders_operation_help(self):
        # The operation token precedes --help, so help resolves at operation
        # level.  Assert a positive operation-only marker (a describe-instances
        # parameter) so the test fails if nothing renders, not merely the
        # absence of the service-help "Available Commands" section.
        self.driver.main(['ec2', 'describe-instances', '--help'])
        self.assert_contains('--instance-ids')  # operation help rendered
        self.assert_not_contains('Available Commands')  # and NOT service help

    def test_flag_before_command_at_provider_renders_provider_help(self):
        # aws --help ec2  ->  provider help, not ec2 help.  The provider help
        # lists services under "Available Commands"; ec2 (service) help lists
        # operations.  Both contain the string, so we assert the provider-only
        # synopsis line instead.
        self.driver.main(['--help', 'ec2'])
        self.assert_contains('The AWS Command Line Interface')

    def test_flag_before_subcommand_renders_parent_help(self):
        # aws configure --help get  ->  configure help (parent), not get help.
        self.driver.main(['configure', '--help', 'get'])
        self.assert_contains('Available Commands')

    def test_flag_after_subcommand_renders_subcommand_help(self):
        # aws configure get --help  ->  `get` help.  Assert a positive
        # subcommand-only marker (the `get` command's own description) so the
        # test fails if nothing renders, not merely the absence of the
        # "Available Commands" section (`get` has no subcommands).
        self.driver.main(['configure', 'get', '--help'])
        self.assert_contains(
            'Get a configuration value'
        )  # `get` help rendered
        self.assert_not_contains(
            'Available Commands'
        )  # and not a parent listing


class TestHelpFlagSkipsOptionValues(BaseAWSHelpOutputTest):
    """A value that happens to name a command/operation must not be mistaken for
    one.  Routing parses the pre-help slice, so the values of value-taking
    global options are consumed by argparse rather than read as a command.
    These mirror the positional ``help`` token: ``aws --region ec2 --help``
    renders provider help because ``ec2`` is --region's value, not the command.
    """

    def test_option_value_naming_a_command_renders_provider_help(self):
        # aws --region ec2 --help  ==  aws --region ec2 help  ->  provider help.
        # `ec2` is --region's VALUE, not the command.
        self.driver.main(['--region', 'ec2', '--help'])
        self.assert_contains('The AWS Command Line Interface')

    def test_valid_global_value_then_flag_renders_provider_help(self):
        self.driver.main(['--region', 'us-west-2', '--help'])
        self.assert_contains('The AWS Command Line Interface')

    def test_global_value_at_service_renders_service_help(self):
        # aws ec2 --output json --help  ->  EC2 service help (option json is a
        # valid --output value; no operation is named before --help).
        self.driver.main(['ec2', '--output', 'json', '--help'])
        self.assert_contains('Available Commands')  # service help
