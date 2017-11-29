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
import time
import signal
import os
import tempfile
import random
import shutil

import botocore.session
from awscli.testutils import unittest, aws, BaseS3CLICommand
from awscli.testutils import temporary_file
from awscli.testutils import skip_if_windows
from awscli.clidriver import create_clidriver


class TestBasicCommandFunctionality(unittest.TestCase):
    """
    These are a set of tests that assert high level features of
    the CLI.  They don't anything exhaustive and is meant as a smoke
    test to verify basic CLI functionality isn't entirely broken.
    """

    def put_object(self, bucket, key, content, extra_args=None):
        session = botocore.session.get_session()
        client = session.create_client('s3', 'us-east-1')
        client.create_bucket(Bucket=bucket)
        time.sleep(5)
        self.addCleanup(client.delete_bucket, Bucket=bucket)
        call_args = {
            'Bucket': bucket,
            'Key': key, 'Body': content
        }
        if extra_args is not None:
            call_args.update(extra_args)
        client.put_object(**call_args)
        self.addCleanup(client.delete_object, Bucket=bucket, Key=key)

    def test_ec2_describe_instances(self):
        # Verify we can make a call and get output.
        p = aws('ec2 describe-instances')
        self.assertEqual(p.rc, 0)
        # We don't know what instances a user might have, but we know
        # there should at least be a Reservations key.
        self.assertIn('Reservations', p.json)

    def test_help_output(self):
        p = aws('help')
        self.assertEqual(p.rc, 0)
        self.assertIn('AWS', p.stdout)
        self.assertRegexpMatches(
            p.stdout, 'The\s+AWS\s+Command\s+Line\s+Interface')

    def test_service_help_output(self):
        p = aws('ec2 help')
        self.assertEqual(p.rc, 0)
        self.assertIn('Amazon EC2', p.stdout)

    def test_operation_help_output(self):
        p = aws('ec2 describe-instances help')
        self.assertEqual(p.rc, 0)
        # XXX: This is a rendering bug that needs to be fixed in bcdoc.  In
        # the RST version there are multiple spaces between certain words.
        # For now we're making the test less strict about formatting, but
        # we eventually should update this test to check exactly for
        # 'The describe-instances operation'.
        self.assertRegexpMatches(p.stdout,
                                 '\s+Describes\s+one\s+or\s+more')

    def test_topic_list_help_output(self):
        p = aws('help topics')
        self.assertEqual(p.rc, 0)
        self.assertRegexpMatches(p.stdout, '\s+AWS\s+CLI\s+Topic\s+Guide')
        self.assertRegexpMatches(
            p.stdout,
            '\s+This\s+is\s+the\s+AWS\s+CLI\s+Topic\s+Guide'
        )

    def test_topic_help_output(self):
        p = aws('help return-codes')
        self.assertEqual(p.rc, 0)
        self.assertRegexpMatches(p.stdout, '\s+AWS\s+CLI\s+Return\s+Codes')
        self.assertRegexpMatches(
            p.stdout,
            'These\s+are\s+the\s+following\s+return\s+codes'
        )

    def test_operation_help_with_required_arg(self):
        p = aws('s3api get-object help')
        self.assertEqual(p.rc, 0, p.stderr)
        self.assertIn('get-object', p.stdout)

    def test_service_help_with_required_option(self):
        # In cloudsearchdomain, the --endpoint-url is required.
        # We want to make sure if you're just getting help tex
        # that we don't trigger that validation.
        p = aws('cloudsearchdomain help')
        self.assertEqual(p.rc, 0, p.stderr)
        self.assertIn('cloudsearchdomain', p.stdout)
        # And nothing on stderr about missing options.
        self.assertEqual(p.stderr, '')

    def test_operation_help_with_required_option(self):
        p = aws('cloudsearchdomain search help')
        self.assertEqual(p.rc, 0, p.stderr)
        self.assertIn('search', p.stdout)
        # And nothing on stderr about missing options.
        self.assertEqual(p.stderr, '')

    def test_help_with_warning_blocks(self):
        p = aws('elastictranscoder create-pipeline help')
        self.assertEqual(p.rc, 0, p.stderr)
        # Check text that appears in the warning block to ensure
        # the block was actually rendered.
        self.assertRegexpMatches(p.stdout, 'To\s+receive\s+notifications')

    def test_param_shorthand(self):
        p = aws(
            'ec2 describe-instances --filters Name=instance-id,Values=i-123')
        self.assertEqual(p.rc, 0)
        self.assertIn('Reservations', p.json)

    def test_param_json(self):
        p = aws(
            'ec2 describe-instances --filters '
            '\'{"Name": "instance-id", "Values": ["i-123"]}\'')
        self.assertEqual(p.rc, 0, p.stdout + p.stderr)
        self.assertIn('Reservations', p.json)

    def test_param_with_bad_json(self):
        p = aws(
            'ec2 describe-instances --filters '
            '\'{"Name": "bad-filter", "Values": ["i-123"]}\'')
        self.assertEqual(p.rc, 255)
        self.assertIn("The filter 'bad-filter' is invalid", p.stderr,
                      "stdout: %s, stderr: %s" % (p.stdout, p.stderr))

    def test_param_with_file(self):
        d = tempfile.mkdtemp()
        self.addCleanup(os.rmdir, d)
        param_file = os.path.abspath(os.path.join(d, 'params.json'))
        with open(param_file, 'w') as f:
            f.write('[{"Name": "instance-id", "Values": ["i-123"]}]')
        self.addCleanup(os.remove, param_file)
        p = aws('ec2 describe-instances --filters file://%s' % param_file)
        self.assertEqual(p.rc, 0)
        self.assertIn('Reservations', p.json)

    def test_streaming_output_operation(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        bucket_name = 'clistream' + str(
            int(time.time())) + str(random.randint(1, 100))

        self.put_object(bucket=bucket_name, key='foobar',
                        content='foobar contents')
        p = aws('s3api get-object --bucket %s --key foobar %s' % (
            bucket_name, os.path.join(d, 'foobar')))
        self.assertEqual(p.rc, 0)
        with open(os.path.join(d, 'foobar')) as f:
            contents = f.read()
        self.assertEqual(contents, 'foobar contents')

    def test_no_sign_request(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)

        env_vars = os.environ.copy()
        env_vars['AWS_ACCESS_KEY_ID'] = 'foo'
        env_vars['AWS_SECRET_ACCESS_KEY'] = 'bar'

        bucket_name = 'nosign' + str(
            int(time.time())) + str(random.randint(1, 100))
        self.put_object(bucket_name, 'foo', content='bar',
                        extra_args={'ACL': 'public-read-write'})

        p = aws('s3api get-object --bucket %s --key foo %s' % (
            bucket_name, os.path.join(d, 'foo')), env_vars=env_vars)
        # Should have credential issues.
        self.assertEqual(p.rc, 255)

        p = aws('s3api get-object --bucket %s --key foo '
                '%s --no-sign-request' % (bucket_name, os.path.join(d, 'foo')),
                env_vars=env_vars)

        # Should be able to download the file when not signing.
        self.assertEqual(p.rc, 0)

        with open(os.path.join(d, 'foo')) as f:
            contents = f.read()
        self.assertEqual(contents, 'bar')

    def test_no_paginate_arg(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        bucket_name = 'nopaginate' + str(
            int(time.time())) + str(random.randint(1, 100))

        self.put_object(bucket=bucket_name, key='foobar',
                        content='foobar contents')
        p = aws('s3api list-objects --bucket %s --no-paginate' % bucket_name)
        self.assertEqual(p.rc, 0, p.stdout + p.stderr)

        p = aws('s3api list-objects --bucket %s' % bucket_name)
        self.assertEqual(p.rc, 0, p.stdout + p.stderr)

    def test_top_level_options_debug(self):
        p = aws('ec2 describe-instances --debug')
        self.assertEqual(p.rc, 0)
        self.assertIn('DEBUG', p.stderr)

    def test_make_requests_to_other_region(self):
        p = aws('ec2 describe-instances --region us-west-2')
        self.assertEqual(p.rc, 0)
        self.assertIn('Reservations', p.json)

    def test_help_usage_top_level(self):
        p = aws('')
        self.assertIn('usage: aws [options] <command> '
                      '<subcommand> [<subcommand> ...] [parameters]', p.stderr)
        self.assertIn('aws: error', p.stderr)

    def test_help_usage_service_level(self):
        p = aws('ec2')
        self.assertIn('usage: aws [options] <command> '
                      '<subcommand> [<subcommand> ...] [parameters]', p.stderr)
        # python3: aws: error: the following arguments are required: operation
        # python2: aws: error: too few arguments
        # We don't care too much about the specific error message, as long
        # as it says we have a parse error.
        self.assertIn('aws: error', p.stderr)

    def test_help_usage_operation_level(self):
        p = aws('ec2 start-instances')
        self.assertIn('usage: aws [options] <command> '
                      '<subcommand> [<subcommand> ...] [parameters]', p.stderr)

    def test_unknown_argument(self):
        p = aws('ec2 describe-instances --filterss')
        self.assertEqual(p.rc, 255)
        self.assertIn('Unknown options: --filterss', p.stderr)

    def test_table_output(self):
        p = aws('ec2 describe-instances --output table --color off')
        # We're not testing the specifics of table output, we just want
        # to make sure the output looks like a table using some heuristics.
        # If this prints JSON instead of a table, for example, this test
        # should fail.
        self.assertEqual(p.rc, 0, p.stderr)
        self.assertIn('-----', p.stdout)
        self.assertIn('+-', p.stdout)
        self.assertIn('DescribeInstances', p.stdout)

    def test_version(self):
        p = aws('--version')
        self.assertEqual(p.rc, 0)
        # The version is wrote to standard out for Python 3.4 and
        # standard error for other Python versions.
        version_output = p.stderr.startswith('aws-cli') or \
            p.stdout.startswith('aws-cli')
        self.assertTrue(version_output, p.stderr)

    def test_traceback_printed_when_debug_on(self):
        p = aws('ec2 describe-instances --filters BADKEY=foo --debug')
        self.assertIn('Traceback (most recent call last):', p.stderr, p.stderr)
        # Also should see DEBUG statements:
        self.assertIn('DEBUG', p.stderr, p.stderr)

    def test_leftover_args_in_operation(self):
        p = aws('ec2 describe-instances BADKEY=foo')
        self.assertEqual(p.rc, 255)
        self.assertIn("Unknown option", p.stderr, p.stderr)

    def test_json_param_parsing(self):
        # This is convered by unit tests in botocore, but this is a sanity
        # check that we get a json response from a json service.
        p = aws('swf list-domains --registration-status REGISTERED')
        self.assertEqual(p.rc, 0)
        self.assertIsInstance(p.json, dict)

        p = aws('dynamodb list-tables')
        self.assertEqual(p.rc, 0)
        self.assertIsInstance(p.json, dict)

    def test_pagination_with_text_output(self):
        p = aws('iam list-users --output text')
        self.assertEqual(p.rc, 0)

    def test_bad_lc_ctype_env_var_is_handled(self):
        # Test for bad LC_CTYPE on Mac OS X.
        base_env_vars = os.environ.copy()
        base_env_vars['LC_CTYPE'] = 'UTF-8'
        p = aws('iam list-users', env_vars=base_env_vars)
        self.assertEqual(p.rc, 0)

    def test_error_msg_with_no_region_configured(self):
        environ = os.environ.copy()
        try:
            del environ['AWS_DEFAULT_REGION']
        except KeyError:
            pass
        environ['AWS_CONFIG_FILE'] = 'nowhere-foo'
        p = aws('ec2 describe-instances', env_vars=environ)
        self.assertIn('must specify a region', p.stderr)

    @skip_if_windows('Ctrl-C not supported on windows.')
    def test_ctrl_c_does_not_print_traceback(self):
        # Relying on the fact that this generally takes
        # more than 1 second to complete.
        process = aws('ec2 describe-images', wait_for_finish=False)
        time.sleep(1)
        process.send_signal(signal.SIGINT)
        stdout, stderr = process.communicate()
        self.assertNotIn(b'Traceback', stdout)
        self.assertNotIn(b'Traceback', stderr)


class TestCommandLineage(unittest.TestCase):
    def setUp(self):
        self.driver = create_clidriver()
        self.top_help = self.driver.create_help_command()

    def assert_lineage_names(self, ref_lineage_names):
        command_table = self.top_help.command_table
        for i, cmd_name in enumerate(ref_lineage_names):
            command = command_table[cmd_name]
            help_command = command.create_help_command()
            command_table = help_command.command_table

        actual_lineage_names = []
        for cmd in command.lineage:
            actual_lineage_names.append(cmd.name)

        # Assert the actual names of each command in a lineage is as expected.
        self.assertEqual(actual_lineage_names, ref_lineage_names)

        # Assert that ``lineage_names`` for each command is in sync with what
        # is actually in the command's ``lineage``.
        self.assertEqual(command.lineage_names, actual_lineage_names)

    def test_service_level_commands(self):
        # Check a normal unchanged service command
        self.assert_lineage_names(['ec2'])

        # Check a service that had its name changed.
        self.assert_lineage_names(['s3api'])

        # Check a couple custom service level commands.
        self.assert_lineage_names(['s3'])
        self.assert_lineage_names(['configure'])

    def test_operation_level_commands(self):
        # Check a normal unchanged service and operation command
        self.assert_lineage_names(['dynamodb', 'create-table'])

        # Check an operation commands with a service that had its name changed.
        self.assert_lineage_names(['s3api', 'list-objects'])

        # Check a custom operation level command with no
        # custom service command.
        self.assert_lineage_names(['emr', 'create-cluster'])

        # Check a couple of operation level commands that
        # are based off a custom service command
        self.assert_lineage_names(['configure', 'set'])
        self.assert_lineage_names(['s3', 'cp'])

    def test_wait_commands(self):
        self.assert_lineage_names(['ec2', 'wait'])
        self.assert_lineage_names(['ec2', 'wait', 'instance-running'])


# We're using BaseS3CLICommand because we need a service to use
# for testing the global arguments.  We're picking S3 here because
# the BaseS3CLICommand has a lot of utility functions that help
# with this.
class TestGlobalArgs(BaseS3CLICommand):

    def test_endpoint_url(self):
        p = aws('s3api list-objects --bucket dnscompat '
                '--endpoint-url http://localhost:51515 '
                '--debug')
        debug_logs = p.stderr
        original_hostname = 'dnscompat.s3.amazonaws.com'
        expected = 'localhost'
        self.assertNotIn(original_hostname, debug_logs,
                         '--endpoint-url is being ignored.')
        self.assertIn(expected, debug_logs)

    def test_no_pagination(self):
        bucket_name = self.create_bucket()
        self.put_object(bucket_name, 'foo.txt', contents=b'bar')
        self.put_object(bucket_name, 'foo2.txt', contents=b'bar')
        self.put_object(bucket_name, 'foo3.txt', contents=b'bar')
        p = aws('s3api list-objects --bucket %s '
                '--no-paginate --output json' % bucket_name)
        # A really simple way to check that --no-paginate was
        # honored is to see if we have all the mirrored input
        # arguments in the response json.  These normally aren't
        # present when the response is paginated.
        self.assert_no_errors(p)
        response_json = p.json
        self.assertIn('IsTruncated', response_json)
        self.assertIn('Name', response_json)

    def test_no_paginate_and_original_args(self):
        bucket_name = self.create_bucket()
        self.put_object(bucket_name, 'foo.txt', contents=b'bar')
        self.put_object(bucket_name, 'foo2.txt', contents=b'bar')
        self.put_object(bucket_name, 'foo3.txt', contents=b'bar')
        p = aws('s3api list-objects --bucket %s '
                '--max-keys 1 --no-paginate --output json' % bucket_name)
        self.assert_no_errors(p)
        response_json = p.json
        self.assertEqual(len(response_json['Contents']), 1)

    def test_max_items(self):
        bucket_name = self.create_bucket()
        self.put_object(bucket_name, 'foo.txt', contents=b'bar')
        self.put_object(bucket_name, 'foo2.txt', contents=b'bar')
        self.put_object(bucket_name, 'foo3.txt', contents=b'bar')
        p = aws('s3api list-objects --bucket %s '
                '--max-items 1 --output json' % bucket_name)
        self.assert_no_errors(p)
        response_json = p.json
        self.assertEqual(len(response_json['Contents']), 1)

    def test_query(self):
        bucket_name = self.create_bucket()
        self.put_object(bucket_name, 'foo.txt', contents=b'bar')
        p = aws('s3api list-objects --bucket %s '
                '--query Contents[].Key --output json' % bucket_name)
        self.assert_no_errors(p)
        response_json = p.json
        self.assertEqual(response_json, ['foo.txt'])

    def test_no_sign_requests(self):
        bucket_name = self.create_bucket()
        self.put_object(bucket_name, 'public', contents=b'bar',
                        extra_args={'ACL': 'public-read'})
        self.put_object(bucket_name, 'private', contents=b'bar')
        env = os.environ.copy()
        # Set the env vars to bad values so if we do actually
        # try to sign the request, we'll get an auth error.
        env['AWS_ACCESS_KEY_ID'] = 'foo'
        env['AWS_SECRET_ACCESS_KEY'] = 'bar'
        p = aws('s3api head-object --bucket %s --key public --no-sign-request'
                % bucket_name, env_vars=env)
        self.assert_no_errors(p)
        self.assertIn('ETag', p.json)

        # Should fail because we're not signing the request but the object is
        # private.
        p = aws('s3api head-object --bucket %s --key private --no-sign-request'
                % bucket_name, env_vars=env)
        self.assertEqual(p.rc, 255)

    def test_profile_arg_has_precedence_over_env_vars(self):
        # At a high level, we're going to set access_key/secret_key
        # via env vars, but ensure that a --profile <foo> results
        # in creds being retrieved from the shared creds file
        # and not from env vars.
        env_vars = os.environ.copy()
        with temporary_file('w') as f:
            env_vars.pop('AWS_PROFILE', None)
            env_vars.pop('AWS_DEFAULT_PROFILE', None)
            # 'aws configure list' only shows 4 values
            # from the credentials so we'll show
            # 4 char values.
            env_vars['AWS_ACCESS_KEY_ID'] = 'enva'
            env_vars['AWS_SECRET_ACCESS_KEY'] = 'envb'
            env_vars['AWS_SHARED_CREDENTIALS_FILE'] = f.name
            env_vars['AWS_CONFIG_FILE'] = 'does-not-exist-foo'
            f.write(
                '[from_argument]\n'
                'aws_access_key_id=proa\n'
                'aws_secret_access_key=prob\n'
            )
            f.flush()
            p = aws('configure list --profile from_argument',
                    env_vars=env_vars)
            # 1. We should see the profile name being set.
            self.assertIn('from_argument', p.stdout)
            # 2. The creds should be proa/prob, which come
            #    from the "from_argument" profile.
            self.assertIn('proa', p.stdout)
            self.assertIn('prob', p.stdout)
            self.assertIn('shared-credentials-file', p.stdout)

    def test_profile_arg_wins_over_profile_env_var(self):
        env_vars = os.environ.copy()
        with temporary_file('w') as f:
            # Remove existing profile related env vars.
            env_vars.pop('AWS_PROFILE', None)
            env_vars.pop('AWS_DEFAULT_PROFILE', None)
            env_vars['AWS_SHARED_CREDENTIALS_FILE'] = f.name
            env_vars['AWS_CONFIG_FILE'] = 'does-not-exist-foo'
            f.write(
                '[from_env_var]\n'
                'aws_access_key_id=enva\n'
                'aws_secret_access_key=envb\n'
                '\n'
                '[from_argument]\n'
                'aws_access_key_id=proa\n'
                'aws_secret_access_key=prob\n'
            )
            f.flush()
            # Now we set the current profile via env var:
            env_vars['AWS_PROFILE'] = 'from_env_var'
            # If we specify the --profile argument, that
            # value should win over the AWS_PROFILE env var.
            p = aws('configure list --profile from_argument',
                    env_vars=env_vars)
            # 1. We should see the profile name being set.
            self.assertIn('from_argument', p.stdout)
            # 2. The creds should be profa/profb, which come
            #    from the "from_argument" profile.
            self.assertIn('proa', p.stdout)
            self.assertIn('prob', p.stdout)


if __name__ == '__main__':
    unittest.main()
