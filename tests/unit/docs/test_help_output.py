#!/usr/bin/env python
"""Test help output for the AWS CLI.

The purpose of these docs is to test that the generated output looks how
we expect.

It's intended to be as end to end as possible, but instead of looking
at the man output, we look one step before at the generated rst output
(it's easier to verify).

"""
from tests import BaseCLIDriverTest

import mock


class CapturedRenderer(object):
    def __init__(self):
        self.rendered_contents = ''

    def render(self, contents):
        self.rendered_contents = contents


class TestAWSHelpOutput(BaseCLIDriverTest):
    def setUp(self):
        super(TestAWSHelpOutput, self).setUp()
        self.renderer_patch = mock.patch('awscli.help.get_renderer')
        self.renderer_mock = self.renderer_patch.start()
        self.renderer = CapturedRenderer()
        self.renderer_mock.return_value = self.renderer

    def tearDown(self):
        super(TestAWSHelpOutput, self).tearDown()
        self.renderer_patch.stop()

    def assert_contains(self, contains):
        if contains not in self.renderer.rendered_contents:
            self.fail("The expected contents:\n%s\nwere not in the "
                      "actual rendered contents:\n%s" % (
                          contains, self.renderer.rendered_contents))

    def assert_text_order(self, *args, **kwargs):
        # First we need to find where the SYNOPSIS section starts.
        starting_from = kwargs.pop('starting_from')
        args = list(args)
        contents = self.renderer.rendered_contents
        self.assertIn(starting_from, contents)
        start_index = contents.find(starting_from)
        arg_indices = [contents.find(arg) for arg in args]
        previous = arg_indices[0]
        for i, index in enumerate(arg_indices[1:], 1):
            if index == -1:
                self.fail('The string %r was not found in the contents: %s'
                          % (args[index], contents))
            if index < previous:
                self.fail('The string %r came before %r, but was suppose to come '
                          'after it.' % (args[i], args[i - 1]))
            previous = index

    def test_output(self):
        self.driver.main(['help'])
        self.assert_contains('***\naws\n***')
        self.assert_contains(
            'The AWS Command Line Interface is a unified tool that provides a '
            'consistent interface for interacting with all parts of AWS')
        # Verify we see the docs for top level params, so pick
        # a few representative types of params.
        self.assert_contains('``--endpoint-url``')
        # Boolean type
        self.assert_contains('``--no-paginate``')
        # Arg with choices
        self.assert_contains('``--color``')
        self.assert_contains('* on')
        self.assert_contains('* off')
        self.assert_contains('* auto')
        # Then we should see the services.
        self.assert_contains('* ec2')
        self.assert_contains('* s3')
        self.assert_contains('* sts')

    def test_service_help_output(self):
        self.driver.main(['ec2', 'help'])
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
        # Should see the title with the operation name
        self.assert_contains('*************\nrun-instances\n*************')
        # Should contain part of the help text from the model.
        self.assert_contains('The run-instances operation launches a specified '
                             'number of instances')
        self.assert_contains('``--max-count`` (integer)')

    def test_arguments_with_example_json_syntax(self):
        self.driver.main(['ec2', 'run-instances', 'help'])
        self.assert_contains('``--iam-instance-profile``')
        self.assert_contains('JSON Syntax')
        self.assert_contains('"arn": "string"')
        self.assert_contains('"name": "string"')

    def test_arguments_with_example_shorthand_syntax(self):
        self.driver.main(['ec2', 'run-instances', 'help'])
        self.assert_contains('``--iam-instance-profile``')
        self.assert_contains('Shorthand Syntax')
        self.assert_contains('--iam-instance-profile arn=value,name=value')

    def test_required_args_come_before_optional_args(self):
        self.driver.main(['ec2', 'run-instances', 'help'])
        # We're asserting that the args in the synopsis section appear
        # in this order.  They don't have to be in this exact order, but
        # each item in the list has to come before the previous arg.
        self.assert_text_order(
            '--image-id <value>',
            '--min-count <value>',
            '--max-count <value>',
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
