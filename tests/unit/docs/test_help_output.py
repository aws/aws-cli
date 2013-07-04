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
        self.assert_contains('The RunInstances operation launches a specified '
                             'number of instances')
        self.assert_contains('``--max-count`` (integer)')
