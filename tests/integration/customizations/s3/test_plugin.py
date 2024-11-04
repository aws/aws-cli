# -*- coding: utf-8 -*-
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

# The following tests are performed to ensure that the commands work.
# It does not check every possible parameter that can be thrown as
# those are checked by tests in other classes
import os
import platform
import contextlib
import time
import stat
import signal
import string
import socket
import tempfile
import shutil
import copy
import logging

import pytest

from awscli.compat import BytesIO, urlopen
import botocore.session

from awscli.testutils import unittest, get_stdout_encoding
from awscli.testutils import skip_if_windows
from awscli.testutils import aws as _aws
from awscli.testutils import BaseS3CLICommand
from awscli.testutils import random_chars, random_bucket_name
from awscli.customizations.s3.transferconfig import DEFAULTS
from awscli.customizations.scalarparse import add_scalar_parsers, identity


# Using the same log name as testutils.py
LOG = logging.getLogger('awscli.tests.integration')
_SHARED_BUCKET = random_bucket_name()
_NON_EXISTENT_BUCKET = random_bucket_name()
_DEFAULT_REGION = 'us-west-2'
_DEFAULT_AZ = 'usw2-az1'
_SHARED_DIR_BUCKET = f'{random_bucket_name()}--{_DEFAULT_AZ}--x-s3'


def setup_module():
    s3 = botocore.session.get_session().create_client('s3')
    waiter = s3.get_waiter('bucket_exists')
    params = {
        'Bucket': _SHARED_BUCKET,
        'CreateBucketConfiguration': {
            'LocationConstraint': _DEFAULT_REGION,
        },
        'ObjectOwnership': 'ObjectWriter'
    }
    dir_bucket_params = {
        'Bucket': _SHARED_DIR_BUCKET,
        'CreateBucketConfiguration': {
            'Location': {
                'Type': 'AvailabilityZone',
                'Name': _DEFAULT_AZ
            },
            'Bucket': {
                'Type': 'Directory',
                'DataRedundancy': 'SingleAvailabilityZone'
            }
        }
    }
    try:
        s3.create_bucket(**params)
        s3.create_bucket(**dir_bucket_params)
    except Exception as e:
        # A create_bucket can fail for a number of reasons.
        # We're going to defer to the waiter below to make the
        # final call as to whether or not the bucket exists.
        LOG.debug("create_bucket() raised an exception: %s", e, exc_info=True)
    waiter.wait(Bucket=_SHARED_BUCKET)
    waiter.wait(Bucket=_SHARED_DIR_BUCKET)
    s3.delete_public_access_block(
        Bucket=_SHARED_BUCKET
    )

    # Validate that "_NON_EXISTENT_BUCKET" doesn't exist.
    waiter = s3.get_waiter('bucket_not_exists')
    try:
        waiter.wait(Bucket=_NON_EXISTENT_BUCKET)
    except Exception as e:
        LOG.debug(
            f"The following bucket was unexpectedly discovered: {_NON_EXISTENT_BUCKET}",
            e,
            exc_info=True,
        )


def clear_out_bucket(bucket, delete_bucket=False):
    s3 = botocore.session.get_session().create_client(
        's3', region_name=_DEFAULT_REGION)
    page = s3.get_paginator('list_objects_v2')
    # Use pages paired with batch delete_objects().
    for page in page.paginate(Bucket=bucket):
        keys = [{'Key': obj['Key']} for obj in page.get('Contents', [])]
        if keys:
            s3.delete_objects(Bucket=bucket, Delete={'Objects': keys})
    if delete_bucket:
        try:
            s3.delete_bucket(Bucket=bucket)
        except Exception as e:
            # We can sometimes get exceptions when trying to
            # delete a bucket.  We'll let the waiter make
            # the final call as to whether the bucket was able
            # to be deleted.
            LOG.debug("delete_bucket() raised an exception: %s",
                      e, exc_info=True)
            waiter = s3.get_waiter('bucket_not_exists')
            waiter.wait(Bucket=bucket)


def teardown_module():
    clear_out_bucket(_SHARED_BUCKET, delete_bucket=True)
    clear_out_bucket(_SHARED_DIR_BUCKET, delete_bucket=True)


@contextlib.contextmanager
def cd(directory):
    original = os.getcwd()
    try:
        os.chdir(directory)
        yield
    finally:
        os.chdir(original)


def aws(command, collect_memory=False, env_vars=None, wait_for_finish=True,
        input_data=None, input_file=None):
    if not env_vars:
        env_vars = os.environ.copy()
        env_vars['AWS_DEFAULT_REGION'] = "us-west-2"
    return _aws(command, collect_memory=collect_memory, env_vars=env_vars,
                wait_for_finish=wait_for_finish, input_data=input_data,
                input_file=input_file)


def wait_for_process_exit(process, timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        rc = process.poll()
        if rc is not None:
            break
        time.sleep(1)
    else:
        process.kill()
        raise AssertionError("CLI did not exist within %s seconds of "
                             "receiving a Ctrl+C" % timeout)


def _running_on_rhel():
    return (
        hasattr(platform, 'linux_distribution') and
        platform.linux_distribution()[0] == 'Red Hat Enterprise Linux Server')


class BaseS3IntegrationTest(BaseS3CLICommand):

    def setUp(self):
        clear_out_bucket(_SHARED_BUCKET)
        clear_out_bucket(_SHARED_DIR_BUCKET)
        super(BaseS3IntegrationTest, self).setUp()


class TestMoveCommand(BaseS3IntegrationTest):
    def assert_mv_local_to_s3(self, bucket_name):
        full_path = self.files.create_file('foo.txt', 'this is foo.txt')
        p = aws('s3 mv %s s3://%s/foo.txt' % (full_path,
                                                bucket_name))
        self.assert_no_errors(p)
        # When we move an object, the local file is gone:
        self.assertTrue(not os.path.exists(full_path))
        # And now resides in s3.
        self.assert_key_contents_equal(bucket_name, 'foo.txt',
                                        'this is foo.txt')

    def assert_mv_s3_to_local(self, bucket_name):
        self.put_object(bucket_name, 'foo.txt', 'this is foo.txt')
        full_path = self.files.full_path('foo.txt')
        self.assertTrue(self.key_exists(bucket_name, key_name='foo.txt'))
        p = aws('s3 mv s3://%s/foo.txt %s' % (bucket_name, full_path))
        self.assert_no_errors(p)
        self.assertTrue(os.path.exists(full_path))
        with open(full_path, 'r') as f:
            self.assertEqual(f.read(), 'this is foo.txt')
        # The s3 file should not be there anymore.
        self.assertTrue(self.key_not_exists(bucket_name, key_name='foo.txt'))

    def assert_mv_s3_to_s3(self, from_bucket, create_bucket_call):
        to_bucket = create_bucket_call()
        self.put_object(from_bucket, 'foo.txt', 'this is foo.txt')

        p = aws('s3 mv s3://%s/foo.txt s3://%s/foo.txt' % (from_bucket,
                                                           to_bucket))
        self.assert_no_errors(p)
        contents = self.get_key_contents(to_bucket, 'foo.txt')
        self.assertEqual(contents, 'this is foo.txt')
        # And verify that the object no longer exists in the from_bucket.
        self.assertTrue(self.key_not_exists(from_bucket, key_name='foo.txt'))

    def test_mv_local_to_s3(self):
        self.assert_mv_local_to_s3(_SHARED_BUCKET)

    def test_mv_local_to_s3_express(self):
        self.assert_mv_local_to_s3(_SHARED_DIR_BUCKET)

    def test_mv_s3_to_local(self):
        self.assert_mv_s3_to_local(_SHARED_BUCKET)

    def test_mv_s3_express_to_local(self):
        self.assert_mv_s3_to_local(_SHARED_DIR_BUCKET)

    def test_mv_s3_to_s3(self):
        self.assert_mv_s3_to_s3(_SHARED_BUCKET, self.create_bucket)

    def test_mv_s3_to_s3_express(self):
        self.assert_mv_s3_to_s3(_SHARED_BUCKET, self.create_dir_bucket)

    def test_mv_s3_express_to_s3_express(self):
        self.assert_mv_s3_to_s3(_SHARED_DIR_BUCKET, self.create_dir_bucket)

    def test_mv_s3_express_to_s3(self):
        self.assert_mv_s3_to_s3(_SHARED_DIR_BUCKET, self.create_bucket)

    @pytest.mark.slow
    def test_mv_s3_to_s3_multipart(self):
        from_bucket = _SHARED_BUCKET
        to_bucket = self.create_bucket()
        file_contents = BytesIO(b'abcd' * (1024 * 1024 * 10))
        self.put_object(from_bucket, 'foo.txt', file_contents)

        p = aws('s3 mv s3://%s/foo.txt s3://%s/foo.txt' % (from_bucket,
                                                           to_bucket))
        self.assert_no_errors(p)
        self.assert_key_contents_equal(to_bucket, 'foo.txt', file_contents)
        # And verify that the object no longer exists in the from_bucket.
        self.assertTrue(self.key_not_exists(from_bucket, key_name='foo.txt'))

    def test_mv_s3_to_s3_multipart_recursive(self):
        from_bucket = _SHARED_BUCKET
        to_bucket = self.create_bucket()

        large_file_contents = BytesIO(b'abcd' * (1024 * 1024 * 10))
        small_file_contents = 'small file contents'
        self.put_object(from_bucket, 'largefile', large_file_contents)
        self.put_object(from_bucket, 'smallfile', small_file_contents)

        p = aws('s3 mv s3://%s/ s3://%s/ --recursive' % (from_bucket,
                                                         to_bucket))
        self.assert_no_errors(p)
        # Nothing's in the from_bucket.
        self.assertTrue(self.key_not_exists(from_bucket,
                                            key_name='largefile'))
        self.assertTrue(self.key_not_exists(from_bucket,
                                            key_name='smallfile'))

        # And both files are in the to_bucket.
        self.assertTrue(self.key_exists(to_bucket, key_name='largefile'))
        self.assertTrue(self.key_exists(to_bucket, key_name='smallfile'))

        # And the contents are what we expect.
        self.assert_key_contents_equal(to_bucket, 'smallfile',
                                       small_file_contents)
        self.assert_key_contents_equal(to_bucket, 'largefile',
                                       large_file_contents)

    def test_mv_s3_to_s3_with_sig4(self):
        to_region = 'eu-central-1'
        from_region = 'us-west-2'

        from_bucket = self.create_bucket(region=from_region)
        to_bucket = self.create_bucket(region=to_region)

        file_name = 'hello.txt'
        file_contents = 'hello'
        self.put_object(from_bucket, file_name, file_contents)

        p = aws('s3 mv s3://{0}/{4} s3://{1}/{4} '
                '--source-region {2} --region {3}'
                .format(from_bucket, to_bucket, from_region, to_region,
                        file_name))
        self.assert_no_errors(p)

        self.assertTrue(self.key_not_exists(from_bucket, file_name))
        self.assertTrue(self.key_exists(to_bucket, file_name))

    @pytest.mark.slow
    def test_mv_with_large_file(self):
        bucket_name = _SHARED_BUCKET
        # 40MB will force a multipart upload.
        file_contents = BytesIO(b'abcd' * (1024 * 1024 * 10))
        foo_txt = self.files.create_file(
            'foo.txt', file_contents.getvalue().decode('utf-8'))
        p = aws('s3 mv %s s3://%s/foo.txt' % (foo_txt, bucket_name))
        self.assert_no_errors(p)
        # When we move an object, the local file is gone:
        self.assertTrue(not os.path.exists(foo_txt))
        # And now resides in s3.
        self.assert_key_contents_equal(bucket_name, 'foo.txt', file_contents)

        # Now verify we can download this file.
        p = aws('s3 mv s3://%s/foo.txt %s' % (bucket_name, foo_txt))
        self.assert_no_errors(p)
        self.assertTrue(os.path.exists(foo_txt))
        self.assertEqual(os.path.getsize(foo_txt),
                         len(file_contents.getvalue()))

    def test_mv_to_nonexistent_bucket(self):
        full_path = self.files.create_file('foo.txt', 'this is foo.txt')
        p = aws(f's3 mv {full_path} s3://{_NON_EXISTENT_BUCKET}/foo.txt')
        self.assertEqual(p.rc, 1)

    def test_cant_move_file_onto_itself_small_file(self):
        # We don't even need a remote file in this case.  We can
        # immediately validate that we can't move a file onto itself.
        bucket_name = _SHARED_BUCKET
        self.put_object(bucket_name, key_name='key.txt', contents='foo')
        p = aws('s3 mv s3://%s/key.txt s3://%s/key.txt' %
                (bucket_name, bucket_name))
        self.assertEqual(p.rc, 255)
        self.assertIn('Cannot mv a file onto itself', p.stderr)

    def test_cant_move_large_file_onto_itself(self):
        # At the API level, you can multipart copy an object onto itself,
        # but a mv command doesn't make sense because a mv is just a
        # cp + an rm of the src file.  We should be consistent and
        # not allow large files to be mv'd onto themselves.
        file_contents = BytesIO(b'a' * (1024 * 1024 * 10))
        bucket_name = _SHARED_BUCKET
        self.put_object(bucket_name, key_name='key.txt',
                        contents=file_contents)
        p = aws('s3 mv s3://%s/key.txt s3://%s/key.txt' %
                (bucket_name, bucket_name))
        self.assertEqual(p.rc, 255)
        self.assertIn('Cannot mv a file onto itself', p.stderr)


class TestRm(BaseS3IntegrationTest):
    def assert_rm_with_page_size(self, bucket_name):
        self.put_object(bucket_name, 'foo.txt', contents='hello world')
        self.put_object(bucket_name, 'bar.txt', contents='hello world2')
        p = aws('s3 rm s3://%s/ --recursive --page-size 1' % bucket_name)
        self.assert_no_errors(p)

        self.assertTrue(self.key_not_exists(bucket_name, key_name='foo.txt'))
        self.assertTrue(self.key_not_exists(bucket_name, key_name='bar.txt'))
    @skip_if_windows('Newline in filename test not valid on windows.')
    # Windows won't let you do this.  You'll get:
    # [Errno 22] invalid mode ('w') or filename:
    # 'c:\\windows\\temp\\tmp0fv8uu\\foo\r.txt'
    def test_rm_with_newlines(self):
        bucket_name = _SHARED_BUCKET

        # Note the carriage return in the key name.
        foo_txt = self.files.create_file('foo\r.txt', 'this is foo.txt')
        p = aws('s3 cp %s s3://%s/foo\r.txt' % (foo_txt, bucket_name))
        self.assert_no_errors(p)

        # Make sure object is in bucket.
        self.assertTrue(self.key_exists(bucket_name, key_name='foo\r.txt'))

        # Then delete the file.
        p = aws('s3 rm s3://%s/ --recursive' % (bucket_name,))

        # And verify it's gone.
        self.assertTrue(self.key_not_exists(bucket_name, key_name='foo\r.txt'))

    def test_rm_with_page_size(self):
        self.assert_rm_with_page_size(_SHARED_BUCKET)

    def test_s3_express_rm_with_page_size(self):
        self.assert_rm_with_page_size(_SHARED_DIR_BUCKET)


class TestCp(BaseS3IntegrationTest):

    def assert_cp_to_and_from_s3(self, bucket_name):
        # This tests the ability to put a single file in s3
        # move it to a different bucket.
        # and download the file locally

        # copy file into bucket.
        foo_txt = self.files.create_file('foo.txt', 'this is foo.txt')
        p = aws('s3 cp %s s3://%s/foo.txt' % (foo_txt, bucket_name))
        self.assert_no_errors(p)

        # Make sure object is in bucket.
        self.assertTrue(self.key_exists(bucket_name, key_name='foo.txt'))
        self.assertEqual(
            self.get_key_contents(bucket_name, key_name='foo.txt'),
            'this is foo.txt')

        self.assertEqual(
            self.content_type_for_key(bucket_name, key_name='foo.txt'),
            'text/plain')

        # Make a new name for the file and copy it locally.
        full_path = self.files.full_path('bar.txt')
        p = aws('s3 cp s3://%s/foo.txt %s' % (bucket_name, full_path))
        self.assert_no_errors(p)

        with open(full_path, 'r') as f:
            self.assertEqual(f.read(), 'this is foo.txt')

    def test_cp_to_and_from_s3(self):
        self.assert_cp_to_and_from_s3(_SHARED_BUCKET)

    def test_cp_to_and_from_s3_express(self):
        self.assert_cp_to_and_from_s3(_SHARED_DIR_BUCKET)

    def test_cp_without_trailing_slash(self):
        # There's a unit test for this, but we still want to verify this
        # with an integration test.
        bucket_name = _SHARED_BUCKET

        # copy file into bucket.
        foo_txt = self.files.create_file('foo.txt', 'this is foo.txt')
        # Note that the destination has no trailing slash.
        p = aws('s3 cp %s s3://%s' % (foo_txt, bucket_name))
        self.assert_no_errors(p)

        # Make sure object is in bucket.
        self.assertTrue(self.key_exists(bucket_name, key_name='foo.txt'))
        self.assertEqual(
            self.get_key_contents(bucket_name, key_name='foo.txt'),
            'this is foo.txt')

    @pytest.mark.slow
    def test_cp_s3_s3_multipart(self):
        from_bucket = _SHARED_BUCKET
        to_bucket = self.create_bucket()
        file_contents = BytesIO(b'abcd' * (1024 * 1024 * 10))
        self.put_object(from_bucket, 'foo.txt', file_contents)

        p = aws('s3 cp s3://%s/foo.txt s3://%s/foo.txt' %
                (from_bucket, to_bucket))
        self.assert_no_errors(p)
        self.assert_key_contents_equal(to_bucket, 'foo.txt', file_contents)
        self.assertTrue(self.key_exists(from_bucket, key_name='foo.txt'))

    def test_guess_mime_type(self):
        bucket_name = _SHARED_BUCKET
        bar_png = self.files.create_file('bar.jpeg', 'fake png image')
        p = aws('s3 cp %s s3://%s/bar.jpeg' % (bar_png, bucket_name))
        self.assert_no_errors(p)

        # We should have correctly guessed the content type based on the
        # filename extension.
        self.assertEqual(
            self.content_type_for_key(bucket_name, key_name='bar.jpeg'),
            'image/jpeg')

    @pytest.mark.slow
    def test_download_large_file(self):
        # This will force a multipart download.
        bucket_name = _SHARED_BUCKET
        foo_contents = BytesIO(b'abcd' * (1024 * 1024 * 10))
        self.put_object(bucket_name, key_name='foo.txt',
                        contents=foo_contents)
        local_foo_txt = self.files.full_path('foo.txt')
        p = aws('s3 cp s3://%s/foo.txt %s' % (bucket_name, local_foo_txt))
        self.assert_no_errors(p)
        self.assertEqual(os.path.getsize(local_foo_txt),
                         len(foo_contents.getvalue()))

    @pytest.mark.slow
    @skip_if_windows('SIGINT not supported on Windows.')
    def test_download_ctrl_c_does_not_hang(self):
        bucket_name = _SHARED_BUCKET
        foo_contents = BytesIO(b'abcd' * (1024 * 1024 * 40))
        self.put_object(bucket_name, key_name='foo.txt',
                        contents=foo_contents)
        local_foo_txt = self.files.full_path('foo.txt')
        # --quiet is added to make sure too much output is not communicated
        # to the PIPE, causing a deadlock when not consumed.
        process = aws('s3 cp s3://%s/foo.txt %s --quiet' %
                      (bucket_name, local_foo_txt), wait_for_finish=False)
        # Give it some time to start up and enter it's main task loop.
        time.sleep(3)
        # The process has 60 seconds to finish after being sent a Ctrl+C,
        # otherwise the test fails.
        process.send_signal(signal.SIGINT)
        wait_for_process_exit(process, timeout=60)
        # A Ctrl+C should have a non-zero RC.
        # We either caught the process in
        # its main polling loop (rc=1), or it was successfully terminated by
        # the SIGINT (rc=-2).
        #
        # There is also the chance the interrupt happened before the transfer
        # process started or even after transfer process finished. So the
        # signal may have never been encountered, resulting in an rc of 0.
        # Therefore, it is acceptable to have an rc of 0 as the important part
        # about this test is that it does not hang.
        self.assertIn(process.returncode, [0, 1, -2])

    @pytest.mark.slow
    @skip_if_windows('SIGINT not supported on Windows.')
    def test_cleans_up_aborted_uploads(self):
        bucket_name = _SHARED_BUCKET
        foo_txt = self.files.create_file('foo.txt', '')
        with open(foo_txt, 'wb') as f:
            for i in range(20):
                f.write(b'a' * 1024 * 1024)
        # --quiet is added to make sure too much output is not communicated
        # to the PIPE, causing a deadlock when not consumed.
        process = aws('s3 cp %s s3://%s/ --quiet' % (foo_txt, bucket_name),
                      wait_for_finish=False)
        time.sleep(3)
        # The process has 60 seconds to finish after being sent a Ctrl+C,
        # otherwise the test fails.
        process.send_signal(signal.SIGINT)
        wait_for_process_exit(process, timeout=60)
        uploads_after = self.client.list_multipart_uploads(
            Bucket=bucket_name).get('Uploads', [])
        self.assertEqual(uploads_after, [],
                         "Not all multipart uploads were properly "
                         "aborted after receiving Ctrl-C: %s" % uploads_after)

    def test_cp_to_nonexistent_bucket(self):
        foo_txt = self.files.create_file('foo.txt', 'this is foo.txt')
        p = aws(f's3 cp {foo_txt} s3://{_NON_EXISTENT_BUCKET}/foo.txt')
        self.assertEqual(p.rc, 1)

    def test_cp_empty_file(self):
        bucket_name = _SHARED_BUCKET
        foo_txt = self.files.create_file('foo.txt', contents='')
        p = aws('s3 cp %s s3://%s/' % (foo_txt, bucket_name))
        self.assertEqual(p.rc, 0)
        self.assertNotIn('failed', p.stderr)
        self.assertTrue(self.key_exists(bucket_name, 'foo.txt'))

    def test_download_non_existent_key(self):
        p = aws(f's3 cp s3://{_NON_EXISTENT_BUCKET}/foo.txt foo.txt')
        self.assertEqual(p.rc, 1)
        expected_err_msg = (
            'An error occurred (404) when calling the '
            'HeadObject operation: Key "foo.txt" does not exist')
        self.assertIn(expected_err_msg, p.stderr)

    def test_download_encrypted_kms_object(self):
        bucket_name = self.create_bucket(region='eu-central-1')
        extra_args = {
            'ServerSideEncryption': 'aws:kms',
            'SSEKMSKeyId': 'alias/aws/s3'
        }
        object_name = 'foo.txt'
        contents = 'this is foo.txt'
        self.put_object(bucket_name, object_name, contents,
                        extra_args=extra_args)
        local_filename = self.files.full_path('foo.txt')
        p = aws('s3 cp s3://%s/%s %s --region eu-central-1' %
                (bucket_name, object_name, local_filename))
        self.assertEqual(p.rc, 0)
        # Assert that the file was downloaded properly.
        with open(local_filename, 'r') as f:
            self.assertEqual(f.read(), contents)

    def test_download_empty_object(self):
        bucket_name = _SHARED_BUCKET
        object_name = 'empty-object'
        self.put_object(bucket_name, object_name, '')
        local_filename = self.files.full_path('empty.txt')
        p = aws('s3 cp s3://%s/%s %s' % (
            bucket_name, object_name, local_filename))
        self.assertEqual(p.rc, 0)
        # Assert that the file was downloaded and has no content.
        with open(local_filename, 'r') as f:
            self.assertEqual(f.read(), '')

    def test_website_redirect_ignore_paramfile(self):
        bucket_name = _SHARED_BUCKET
        foo_txt = self.files.create_file('foo.txt', 'bar')
        website_redirect = 'http://someserver'
        p = aws('s3 cp %s s3://%s/foo.txt --website-redirect %s' %
                (foo_txt, bucket_name, website_redirect))
        self.assert_no_errors(p)

        # Ensure that the web address is used as opposed to the contents
        # of the web address. We can check via a head object.
        response = self.head_object(bucket_name, 'foo.txt')
        self.assertEqual(response['WebsiteRedirectLocation'], website_redirect)

    @pytest.mark.slow
    def test_copy_large_file_signature_v4(self):
        # Just verify that we can upload a large file to a region
        # that uses signature version 4.
        bucket_name = self.create_bucket(region='eu-central-1')
        num_mb = 200
        foo_txt = self.files.create_file('foo.txt', '')
        with open(foo_txt, 'wb') as f:
            for i in range(num_mb):
                f.write(b'a' * 1024 * 1024)

        p = aws('s3 cp %s s3://%s/ --region eu-central-1' % (
            foo_txt, bucket_name))
        self.assert_no_errors(p)
        self.assertTrue(self.key_exists(bucket_name, key_name='foo.txt'))

    def test_copy_metadata(self):
        # Copy the same style of parsing as the CLI session. This is needed
        # For comparing expires timestamp.
        add_scalar_parsers(self.session)
        bucket_name = _SHARED_BUCKET
        key = random_chars(6)
        filename = self.files.create_file(key, contents='')
        p = aws('s3 cp %s s3://%s/%s --metadata keyname=value' %
                (filename, bucket_name, key))
        self.assert_no_errors(p)
        response = self.head_object(bucket_name, key)
        # These values should have the metadata of the source object
        self.assertEqual(response['Metadata'].get('keyname'), 'value')

    def test_copy_metadata_directive(self):
        # Copy the same style of parsing as the CLI session. This is needed
        # For comparing expires timestamp.
        self.override_parser(timestamp_parser=identity)
        bucket_name = _SHARED_BUCKET
        original_key = '%s-a' % random_chars(6)
        new_key = '%s-b' % random_chars(6)
        metadata = {
            'ContentType': 'foo',
            'ContentDisposition': 'foo',
            'ContentEncoding': 'foo',
            'ContentLanguage': 'foo',
            'CacheControl': '90',
            'Expires': '0'
        }
        self.put_object(bucket_name, original_key, contents='foo',
                        extra_args=metadata)
        p = aws('s3 cp s3://%s/%s s3://%s/%s' %
                (bucket_name, original_key, bucket_name, new_key))
        self.assert_no_errors(p)
        response = self.head_object(bucket_name, new_key)
        # These values should have the metadata of the source object
        metadata_ref = copy.copy(metadata)
        metadata_ref['Expires'] = 'Thu, 01 Jan 1970 00:00:00 GMT'
        for name, value in metadata_ref.items():
            self.assertEqual(response[name], value)

        # Use REPLACE to wipe out all of the metadata when copying to a new
        # key.
        new_key = '%s-c' % random_chars(6)
        p = aws('s3 cp s3://%s/%s s3://%s/%s --metadata-directive REPLACE' %
                (bucket_name, original_key, bucket_name, new_key))
        self.assert_no_errors(p)
        response = self.head_object(bucket_name, new_key)
        # Make sure all of the original metadata is gone.
        for name, value in metadata_ref.items():
            self.assertNotEqual(response.get(name), value)

        # Use REPLACE to wipe out all of the metadata but include a new
        # metadata value.
        new_key = '%s-d' % random_chars(6)
        p = aws('s3 cp s3://%s/%s s3://%s/%s --metadata-directive REPLACE '
                '--content-type bar' %
                (bucket_name, original_key, bucket_name, new_key))
        self.assert_no_errors(p)
        response = self.head_object(bucket_name, new_key)
        # Make sure the content type metadata is included
        self.assertEqual(response['ContentType'], 'bar')
        # Make sure all of the original metadata is gone.
        for name, value in metadata_ref.items():
            self.assertNotEqual(response.get(name), value)

    def test_cp_with_request_payer(self):
        bucket_name = _SHARED_BUCKET

        foo_txt = self.files.create_file('foo.txt', 'this is foo.txt')
        p = aws('s3 cp %s s3://%s/mykey --request-payer' % (
                foo_txt, bucket_name))

        # From the S3 API, the only way to for sure know that request payer is
        # working is to set up a bucket with request payer and have another
        # account with permissions make a request to that bucket. If they
        # do not include request payer, they will get an access denied error.
        # Setting this up for an integration test would be tricky as it
        # requires having/creating another account outside of the one running
        # the integration tests. So instead at the very least we want to
        # make sure we can use the parameter, have the command run
        # successfully, and correctly upload the key to S3.
        self.assert_no_errors(p)
        self.assertTrue(self.key_exists(bucket_name, key_name='mykey'))
        self.assertEqual(
            self.get_key_contents(bucket_name, key_name='mykey'),
            'this is foo.txt')


class TestSync(BaseS3IntegrationTest):
    def test_sync_with_plus_chars_paginate(self):
        # This test ensures pagination tokens are url decoded.
        # 1. Create > 2 files with '+' in the filename.
        # 2. Sync up to s3 while the page size is 2.
        # 3. Sync up to s3 while the page size is 2.
        # 4. Verify nothing was synced up down from s3 in step 3.
        bucket_name = _SHARED_BUCKET
        filenames = []
        for i in range(4):
            # Create a file with a space char and a '+' char in the filename.
            # We're interested in testing the filename comparisons, not the
            # mtime comparisons so we're setting the mtime to some time
            # in the past to avoid mtime comparisons interfering with
            # test results.
            mtime = time.time() - 300
            filenames.append(
                self.files.create_file('foo +%06d' % i,
                                       contents='',
                                       mtime=mtime))
        p = aws('s3 sync %s s3://%s/ --page-size 2' %
                (self.files.rootdir, bucket_name))
        self.assert_no_errors(p)
        time.sleep(1)
        p2 = aws('s3 sync %s s3://%s/ --page-size 2'
                 % (self.files.rootdir, bucket_name))
        self.assertNotIn('upload:', p2.stdout)
        self.assertEqual('', p2.stdout)

    def test_s3_to_s3_sync_with_plus_char_paginate(self):
        keynames = []
        for i in range(4):
            keyname = 'foo+%d' % i
            keynames.append(keyname)
            self.files.create_file(keyname, contents='')

        bucket_name = _SHARED_BUCKET
        bucket_name_2 = self.create_bucket()

        p = aws('s3 sync %s s3://%s' % (self.files.rootdir, bucket_name))
        self.assert_no_errors(p)
        for key in keynames:
            self.assertTrue(self.key_exists(bucket_name, key))

        p = aws('s3 sync s3://%s/ s3://%s/ --page-size 2' %
                (bucket_name, bucket_name_2))
        self.assert_no_errors(p)
        for key in keynames:
            self.assertTrue(self.key_exists(bucket_name_2, key))

        p2 = aws('s3 sync s3://%s/ s3://%s/ --page-size 2' %
                 (bucket_name, bucket_name_2))
        self.assertNotIn('copy:', p2.stdout)
        self.assertEqual('', p2.stdout)

    def test_sync_no_resync(self):
        self.files.create_file('xyz123456789', contents='test1')
        self.files.create_file(os.path.join('xyz1', 'test'), contents='test2')
        self.files.create_file(os.path.join('xyz', 'test'), contents='test3')
        bucket_name = _SHARED_BUCKET

        p = aws('s3 sync %s s3://%s' % (self.files.rootdir, bucket_name))
        self.assert_no_errors(p)
        time.sleep(2)
        self.assertTrue(self.key_exists(bucket_name, 'xyz123456789'))
        self.assertTrue(self.key_exists(bucket_name, 'xyz1/test'))
        self.assertTrue(self.key_exists(bucket_name, 'xyz/test'))

        p2 = aws('s3 sync %s s3://%s/' % (self.files.rootdir, bucket_name))
        self.assertNotIn('upload:', p2.stdout)
        self.assertEqual('', p2.stdout)

    def test_sync_to_from_s3(self):
        bucket_name = _SHARED_BUCKET
        foo_txt = self.files.create_file('foo.txt', 'foo contents')
        bar_txt = self.files.create_file('bar.txt', 'bar contents')

        # Sync the directory and the bucket.
        p = aws('s3 sync %s s3://%s' % (self.files.rootdir, bucket_name))
        self.assert_no_errors(p)

        # Ensure both files are in the bucket.
        self.assertTrue(self.key_exists(bucket_name, 'foo.txt'))
        self.assertTrue(self.key_exists(bucket_name, 'bar.txt'))

        # Sync back down.  First remote the local files.
        os.remove(foo_txt)
        os.remove(bar_txt)
        p = aws('s3 sync s3://%s %s' % (bucket_name, self.files.rootdir))
        # The files should be back now.
        self.assertTrue(os.path.isfile(foo_txt))
        self.assertTrue(os.path.isfile(bar_txt))
        with open(foo_txt, 'r') as f:
            self.assertEqual(f.read(), 'foo contents')
        with open(bar_txt, 'r') as f:
            self.assertEqual(f.read(), 'bar contents')

    def test_sync_to_nonexistent_bucket(self):
        self.files.create_file('foo.txt', 'foo contents')
        self.files.create_file('bar.txt', 'bar contents')

        # Sync the directory and the bucket.
        p = aws('s3 sync %s s3://noexist-bkt-nme-1412' % (self.files.rootdir,))
        self.assertEqual(p.rc, 1)

    def test_sync_with_empty_files(self):
        self.files.create_file('foo.txt', 'foo contents')
        self.files.create_file('bar.txt', contents='')
        bucket_name = _SHARED_BUCKET
        p = aws('s3 sync %s s3://%s/' % (self.files.rootdir, bucket_name))
        self.assertEqual(p.rc, 0)
        self.assertNotIn('failed', p.stderr)
        self.assertTrue(
            self.key_exists(bucket_name=bucket_name, key_name='bar.txt'))

    def test_sync_with_delete_option_with_same_prefix(self):
        # Test for issue 440 (https://github.com/aws/aws-cli/issues/440)
        # First, we need to create a directory structure that has a dir with
        # the same prefix as some of the files:
        #
        #  test/foo.txt
        #  test-123.txt
        #  test-321.txt
        #  test.txt
        bucket_name = _SHARED_BUCKET
        # create test/foo.txt
        nested_dir = os.path.join(self.files.rootdir, 'test')
        os.mkdir(nested_dir)
        self.files.create_file(os.path.join(nested_dir, 'foo.txt'),
                               contents='foo.txt contents')
        # Then create test-123.txt, test-321.txt, test.txt.
        self.files.create_file('test-123.txt', 'test-123.txt contents')
        self.files.create_file('test-321.txt', 'test-321.txt contents')
        self.files.create_file('test.txt', 'test.txt contents')

        # Now sync this content up to s3.
        # Allow settling time so that we have a different time between
        # source and destination.
        time.sleep(2)
        p = aws('s3 sync %s s3://%s/' % (self.files.rootdir, bucket_name))
        self.assert_no_errors(p)

        # Now here's the issue.  If we try to sync the contents down
        # with the --delete flag we should *not* see any output, the
        # sync operation should determine that nothing is different and
        # therefore do nothing.  We can just use --dryrun to show the issue.
        p = aws('s3 sync s3://%s/ %s --dryrun --delete' % (
            bucket_name, self.files.rootdir))
        self.assert_no_errors(p)
        # These assertion methods will give better error messages than just
        # checking if the output is empty.
        self.assertNotIn('download:', p.stdout)
        self.assertNotIn('delete:', p.stdout)
        self.assertEqual('', p.stdout)

    def test_sync_with_delete_across_sig4_regions(self):
        src_region = 'us-west-2'
        dst_region = 'eu-central-1'

        src_bucket = self.create_bucket(region=src_region)
        dst_bucket = self.create_bucket(region=dst_region)

        src_key_name = 'hello.txt'
        self.files.create_file(src_key_name, contents='hello')

        p = aws('s3 sync %s s3://%s --region %s' %
                (self.files.rootdir, src_bucket, src_region))
        self.assert_no_errors(p)
        self.assertTrue(self.key_exists(src_bucket, src_key_name))

        self.files.remove_all()

        dst_key_name = 'goodbye.txt'
        self.files.create_file(dst_key_name, contents='goodbye')

        p = aws('s3 sync %s s3://%s --region %s' %
                (self.files.rootdir, dst_bucket, dst_region))
        self.assert_no_errors(p)
        self.assertTrue(self.key_exists(dst_bucket, dst_key_name))
        self.assertTrue(self.key_not_exists(dst_bucket, src_key_name))

        p = aws('s3 sync --delete s3://%s s3://%s '
                '--source-region %s --region %s' %
                (src_bucket, dst_bucket, src_region, dst_region))
        self.assert_no_errors(p)

        self.assertTrue(self.key_exists(src_bucket, src_key_name))
        self.assertTrue(self.key_exists(dst_bucket, src_key_name))
        self.assertTrue(self.key_not_exists(src_bucket, dst_key_name))
        self.assertTrue(self.key_not_exists(dst_bucket, dst_key_name))

    def test_sync_delete_locally(self):
        bucket_name = _SHARED_BUCKET
        file_to_delete = self.files.create_file(
            'foo.txt', contents='foo contents')
        self.put_object(bucket_name, 'bar.txt', contents='bar contents')

        p = aws('s3 sync s3://%s/ %s --delete' % (
            bucket_name, self.files.rootdir))
        self.assert_no_errors(p)

        # Make sure the uploaded file got downloaded and the previously
        # existing local file got deleted
        self.assertTrue(os.path.exists(
            os.path.join(self.files.rootdir, 'bar.txt')))
        self.assertFalse(os.path.exists(file_to_delete))


class TestSourceRegion(BaseS3IntegrationTest):
    def extra_setup(self):
        name_comp = []
        # This creates a non DNS compatible bucket name by making two random
        # sequences of characters and joining them with a period and
        # adding a .com at the end.
        for i in range(2):
            name_comp.append(random_chars(10))
        self.src_name = '.'.join(name_comp + ['com'])
        name_comp = []
        for i in range(2):
            name_comp.append(random_chars(10))
        self.dest_name = '.'.join(name_comp + ['com'])
        self.src_region = 'us-west-1'
        self.dest_region = 'us-east-1'
        self.src_bucket = self.create_bucket(self.src_name, self.src_region)
        self.dest_bucket = self.create_bucket(self.dest_name, self.dest_region)

    def test_cp_region(self):
        self.files.create_file('foo.txt', 'foo')
        p = aws('s3 sync %s s3://%s/ --region %s' %
                (self.files.rootdir, self.src_bucket, self.src_region))
        self.assert_no_errors(p)
        p2 = aws('s3 cp s3://%s/ s3://%s/ --region %s --source-region %s '
                 '--recursive' %
                 (self.src_bucket, self.dest_bucket, self.dest_region,
                  self.src_region))
        self.assertEqual(p2.rc, 0, p2.stdout)
        self.assertTrue(
            self.key_exists(bucket_name=self.dest_bucket, key_name='foo.txt'))

    def test_sync_region(self):
        self.files.create_file('foo.txt', 'foo')
        p = aws('s3 sync %s s3://%s/ --region %s' %
                (self.files.rootdir, self.src_bucket, self.src_region))
        self.assert_no_errors(p)
        p2 = aws('s3 sync s3://%s/ s3://%s/ --region %s --source-region %s ' %
                 (self.src_bucket, self.dest_bucket, self.dest_region,
                  self.src_region))
        self.assertEqual(p2.rc, 0, p2.stdout)
        self.assertTrue(
            self.key_exists(bucket_name=self.dest_bucket, key_name='foo.txt'))

    def test_mv_region(self):
        self.files.create_file('foo.txt', 'foo')
        p = aws('s3 sync %s s3://%s/ --region %s' %
                (self.files.rootdir, self.src_bucket, self.src_region))
        self.assert_no_errors(p)
        p2 = aws('s3 mv s3://%s/ s3://%s/ --region %s --source-region %s '
                 '--recursive' %
                 (self.src_bucket, self.dest_bucket, self.dest_region,
                  self.src_region))
        self.assertEqual(p2.rc, 0, p2.stdout)
        self.assertTrue(
            self.key_exists(bucket_name=self.dest_bucket, key_name='foo.txt'))
        self.assertTrue(
            self.key_not_exists(
                bucket_name=self.src_bucket, key_name='foo.txt'))

    @pytest.mark.slow
    def test_mv_large_file_region(self):
        foo_txt = self.files.create_file('foo.txt', 'a' * 1024 * 1024 * 10)
        p = aws('s3 cp %s s3://%s/foo.txt --region %s' %
                (foo_txt, self.src_bucket, self.src_region))
        self.assert_no_errors(p)

        p2 = aws(
            's3 mv s3://%s/foo.txt s3://%s/ --region %s --source-region %s ' %
            (self.src_bucket, self.dest_bucket, self.dest_region,
             self.src_region)
        )
        self.assert_no_errors(p2)
        self.assertTrue(
            self.key_exists(bucket_name=self.dest_bucket, key_name='foo.txt'))
        self.assertTrue(
            self.key_not_exists(
                bucket_name=self.src_bucket, key_name='foo.txt'))


class TestWarnings(BaseS3IntegrationTest):
    def test_no_exist(self):
        bucket_name = _SHARED_BUCKET
        filename = os.path.join(self.files.rootdir, "no-exists-file")
        p = aws('s3 cp %s s3://%s/' % (filename, bucket_name))
        # If the local path provided by the user is nonexistent for an
        # upload, this should error out.
        self.assertEqual(p.rc, 255, p.stderr)
        self.assertIn('The user-provided path %s does not exist.' %
                      filename, p.stderr)

    @skip_if_windows('Read permissions tests only supported on mac/linux')
    def test_no_read_access(self):
        if os.geteuid() == 0:
            self.skipTest('Cannot completely remove read access as root user.')
        bucket_name = _SHARED_BUCKET
        self.files.create_file('foo.txt', 'foo')
        filename = os.path.join(self.files.rootdir, 'foo.txt')
        permissions = stat.S_IMODE(os.stat(filename).st_mode)
        # Remove read permissions
        permissions = permissions ^ stat.S_IREAD
        os.chmod(filename, permissions)
        p = aws('s3 cp %s s3://%s/' % (filename, bucket_name))
        self.assertEqual(p.rc, 2, p.stderr)
        self.assertIn('warning: Skipping file %s. File/Directory is '
                      'not readable.' % filename, p.stderr)

    @skip_if_windows('Special files only supported on mac/linux')
    def test_is_special_file(self):
        bucket_name = _SHARED_BUCKET
        file_path = os.path.join(self.files.rootdir, 'foo')
        # Use socket for special file.
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(file_path)
        p = aws('s3 cp %s s3://%s/' % (file_path, bucket_name))
        self.assertEqual(p.rc, 2, p.stderr)
        self.assertIn(("warning: Skipping file %s. File is character "
                       "special device, block special device, FIFO, or "
                       "socket." % file_path), p.stderr)


class TestUnableToWriteToFile(BaseS3IntegrationTest):

    @skip_if_windows('Write permissions tests only supported on mac/linux')
    def test_no_write_access_small_file(self):
        bucket_name = _SHARED_BUCKET
        if os.geteuid() == 0:
            self.skipTest(
                'Cannot completely remove write access as root user.')
        os.chmod(self.files.rootdir, 0o444)
        self.put_object(bucket_name, 'foo.txt',
                        contents='Hello world')
        p = aws('s3 cp s3://%s/foo.txt %s' % (
            bucket_name, os.path.join(self.files.rootdir, 'foo.txt')))
        self.assertEqual(p.rc, 1)
        self.assertIn('download failed', p.stderr)

    @skip_if_windows('Write permissions tests only supported on mac/linux')
    def test_no_write_access_large_file(self):
        if os.geteuid() == 0:
            self.skipTest(
                'Cannot completely remove write access as root user.')
        bucket_name = _SHARED_BUCKET
        # We have to use a file like object because using a string
        # would result in the header + body sent as a single packet
        # which effectively disables the expect 100 continue logic.
        # This will result in a test error because we won't follow
        # the temporary redirect for the newly created bucket.
        contents = BytesIO(b'a' * 10 * 1024 * 1024)
        self.put_object(bucket_name, 'foo.txt',
                        contents=contents)
        os.chmod(self.files.rootdir, 0o444)
        p = aws('s3 cp s3://%s/foo.txt %s' % (
            bucket_name, os.path.join(self.files.rootdir, 'foo.txt')))
        self.assertEqual(p.rc, 1)
        self.assertIn('download failed', p.stderr)


@skip_if_windows('Symlink tests only supported on mac/linux')
class TestSymlinks(BaseS3IntegrationTest):
    """
    This class test the ability to follow or not follow symlinks.
    """
    def extra_setup(self):
        self.bucket_name = _SHARED_BUCKET
        self.nested_dir = os.path.join(self.files.rootdir, 'realfiles')
        os.mkdir(self.nested_dir)
        self.sample_file = \
            self.files.create_file(os.path.join(self.nested_dir, 'foo.txt'),
                                   contents='foo.txt contents')
        # Create a symlink to foo.txt.
        os.symlink(self.sample_file, os.path.join(self.files.rootdir,
                                                  'a-goodsymlink'))
        # Create a bad symlink.
        os.symlink('non-existent-file', os.path.join(self.files.rootdir,
                                                     'b-badsymlink'))
        # Create a symlink to directory where foo.txt is.
        os.symlink(self.nested_dir, os.path.join(self.files.rootdir,
                                                 'c-goodsymlink'))

    def test_no_follow_symlinks(self):
        p = aws('s3 sync %s s3://%s/ --no-follow-symlinks' % (
            self.files.rootdir, self.bucket_name))
        self.assert_no_errors(p)
        self.assertTrue(self.key_not_exists(self.bucket_name,
                        'a-goodsymlink'))
        self.assertTrue(self.key_not_exists(self.bucket_name,
                        'b-badsymlink'))
        self.assertTrue(self.key_not_exists(self.bucket_name,
                        'c-goodsymlink/foo.txt'))
        self.assertEqual(self.get_key_contents(self.bucket_name,
                                               key_name='realfiles/foo.txt'),
                         'foo.txt contents')

    def test_follow_symlinks(self):
        # Get rid of the bad symlink first.
        os.remove(os.path.join(self.files.rootdir, 'b-badsymlink'))
        p = aws('s3 sync %s s3://%s/ --follow-symlinks' %
                (self.files.rootdir, self.bucket_name))
        self.assert_no_errors(p)
        self.assertEqual(self.get_key_contents(self.bucket_name,
                                               key_name='a-goodsymlink'),
                         'foo.txt contents')
        self.assertTrue(self.key_not_exists(self.bucket_name,
                        'b-badsymlink'))
        self.assertEqual(
            self.get_key_contents(self.bucket_name,
                                  key_name='c-goodsymlink/foo.txt'),
            'foo.txt contents')
        self.assertEqual(self.get_key_contents(self.bucket_name,
                                               key_name='realfiles/foo.txt'),
                         'foo.txt contents')

    def test_follow_symlinks_default(self):
        # Get rid of the bad symlink first.
        os.remove(os.path.join(self.files.rootdir, 'b-badsymlink'))
        p = aws('s3 sync %s s3://%s/' %
                (self.files.rootdir, self.bucket_name))
        self.assert_no_errors(p)
        self.assertEqual(self.get_key_contents(self.bucket_name,
                                               key_name='a-goodsymlink'),
                         'foo.txt contents')
        self.assertTrue(self.key_not_exists(self.bucket_name,
                        'b-badsymlink'))
        self.assertEqual(
            self.get_key_contents(self.bucket_name,
                                  key_name='c-goodsymlink/foo.txt'),
            'foo.txt contents')
        self.assertEqual(self.get_key_contents(self.bucket_name,
                                               key_name='realfiles/foo.txt'),
                         'foo.txt contents')

    def test_bad_symlink(self):
        p = aws('s3 sync %s s3://%s/' % (self.files.rootdir, self.bucket_name))
        self.assertEqual(p.rc, 2, p.stderr)
        self.assertIn('warning: Skipping file %s. File does not exist.' %
                      os.path.join(self.files.rootdir, 'b-badsymlink'),
                      p.stderr)


class TestUnicode(BaseS3IntegrationTest):
    """
    The purpose of these tests are to ensure that the commands can handle
    unicode characters in both keyname and from those generated for both
    uploading and downloading files.
    """
    def test_cp(self):
        bucket_name = _SHARED_BUCKET
        local_example1_txt = \
            self.files.create_file(u'\u00e9xample.txt', 'example1 contents')
        s3_example1_txt = 's3://%s/%s' % (bucket_name,
                                          os.path.basename(local_example1_txt))
        local_example2_txt = self.files.full_path(u'\u00e9xample2.txt')

        p = aws('s3 cp %s %s' % (local_example1_txt, s3_example1_txt))
        self.assert_no_errors(p)

        # Download the file to the second example2.txt filename.
        p = aws('s3 cp %s %s --quiet' % (s3_example1_txt, local_example2_txt))
        self.assert_no_errors(p)
        with open(local_example2_txt, 'rb') as f:
            self.assertEqual(f.read(), b'example1 contents')

    def test_recursive_cp(self):
        bucket_name = _SHARED_BUCKET
        local_example1_txt = self.files.create_file(u'\u00e9xample.txt',
                                                    'example1 contents')
        local_example2_txt = self.files.create_file(u'\u00e9xample2.txt',
                                                    'example2 contents')
        p = aws('s3 cp %s s3://%s --recursive --quiet' % (
            self.files.rootdir, bucket_name))
        self.assert_no_errors(p)

        os.remove(local_example1_txt)
        os.remove(local_example2_txt)

        p = aws('s3 cp s3://%s %s --recursive --quiet' % (
            bucket_name, self.files.rootdir))
        self.assert_no_errors(p)
        self.assertEqual(open(local_example1_txt).read(), 'example1 contents')
        self.assertEqual(open(local_example2_txt).read(), 'example2 contents')


class TestLs(BaseS3IntegrationTest):
    """
    This tests using the ``ls`` command.
    """

    def assert_ls_with_prefix(self, bucket_name):
        self.put_object(bucket_name, 'foo.txt', 'contents')
        self.put_object(bucket_name, 'foo', 'contents')
        self.put_object(bucket_name, 'bar.txt', 'contents')
        self.put_object(bucket_name, 'subdir/foo.txt', 'contents')
        p = aws('s3 ls s3://%s' % bucket_name)
        self.assertIn('PRE subdir/', p.stdout)
        self.assertIn('8 foo.txt', p.stdout)
        self.assertIn('8 foo', p.stdout)
        self.assertIn('8 bar.txt', p.stdout)

    def assert_ls_recursive(self, bucket_name):
        self.put_object(bucket_name, 'foo.txt', 'contents')
        self.put_object(bucket_name, 'foo', 'contents')
        self.put_object(bucket_name, 'bar.txt', 'contents')
        self.put_object(bucket_name, 'subdir/foo.txt', 'contents')
        p = aws('s3 ls s3://%s --recursive' % bucket_name)
        self.assertIn('8 foo.txt', p.stdout)
        self.assertIn('8 foo', p.stdout)
        self.assertIn('8 bar.txt', p.stdout)
        self.assertIn('8 subdir/foo.txt', p.stdout)

    def test_ls_bucket(self):
        p = aws('s3 ls')
        self.assert_no_errors(p)

    def test_ls_with_no_env_vars(self):
        # By default, the aws() function injects
        # an AWS_DEFAULT_REGION into the env var of the
        # process.  We're verifying that a region does *not*
        # need to be set anywhere.  If we provide our
        # own environ dict, then the aws() function won't
        # inject a region.
        env = os.environ.copy()
        p = aws('s3 ls', env_vars=env)
        self.assert_no_errors(p)

    def test_ls_bucket_with_s3_prefix(self):
        p = aws('s3 ls s3://')
        self.assert_no_errors(p)

    def test_ls_non_existent_bucket(self):
        p = aws(f's3 ls s3://{_NON_EXISTENT_BUCKET}')
        self.assertEqual(p.rc, 255)
        self.assertIn(
            ('An error occurred (NoSuchBucket) when calling the '
             'ListObjectsV2 operation: The specified bucket does not exist'),
            p.stderr)
        # There should be no stdout if we can't find the bucket.
        self.assertEqual(p.stdout, '')

    def test_ls_with_prefix(self):
        self.assert_ls_with_prefix(_SHARED_BUCKET)

    def test_s3_express_ls_with_prefix(self):
        self.assert_ls_with_prefix(_SHARED_DIR_BUCKET)

    def test_ls_recursive(self):
        self.assert_ls_recursive(_SHARED_BUCKET)

    def test_s3_express_ls_recursive(self):
        self.assert_ls_recursive(_SHARED_DIR_BUCKET)

    def test_ls_without_prefix(self):
        # The ls command does not require an s3:// prefix,
        # we're always listing s3 contents.
        bucket_name = _SHARED_BUCKET
        self.put_object(bucket_name, 'foo.txt', 'contents')
        p = aws('s3 ls %s' % bucket_name)
        self.assertEqual(p.rc, 0)
        self.assertIn('foo.txt', p.stdout)

    def test_only_prefix(self):
        bucket_name = _SHARED_BUCKET
        self.put_object(bucket_name, 'temp/foo.txt', 'contents')
        p = aws('s3 ls s3://%s/temp/foo.txt' % bucket_name)
        self.assertEqual(p.rc, 0)
        self.assertIn('foo.txt', p.stdout)

    def test_ls_empty_bucket(self):
        bucket_name = _SHARED_BUCKET
        p = aws('s3 ls %s' % bucket_name)
        # There should not be an error thrown for checking the contents of
        # an empty bucket because no key was specified.
        self.assertEqual(p.rc, 0)

    def test_ls_fail(self):
        bucket_name = _SHARED_BUCKET
        p = aws('s3 ls s3://%s/foo' % bucket_name)
        self.assertEqual(p.rc, 1)

    def test_ls_fail_recursive(self):
        bucket_name = _SHARED_BUCKET
        p = aws('s3 ls s3://%s/bar --recursive' % bucket_name)
        self.assertEqual(p.rc, 1)


class TestMbRb(BaseS3IntegrationTest):
    """
    Tests primarily using ``rb`` and ``mb`` command.
    """
    def extra_setup(self):
        self.bucket_name = random_bucket_name()

    def test_mb_rb(self):
        p = aws('s3 mb s3://%s' % self.bucket_name)
        self.assert_no_errors(p)

        # Give the bucket time to form.
        time.sleep(1)
        response = self.list_buckets()
        self.assertIn(self.bucket_name, [b['Name'] for b in response])

        p = aws('s3 rb s3://%s' % self.bucket_name)
        self.assert_no_errors(p)

    def test_fail_mb_rb(self):
        # Choose a bucket name that already exists.
        p = aws('s3 mb s3://mybucket')
        self.assertIn("BucketAlreadyExists", p.stderr)
        self.assertEqual(p.rc, 1)


class TestOutput(BaseS3IntegrationTest):
    """
    This ensures that arguments that affect output i.e. ``--quiet`` and
    ``--only-show-errors`` behave as expected.
    """
    def test_normal_output(self):
        bucket_name = _SHARED_BUCKET
        foo_txt = self.files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s/' % (foo_txt, bucket_name))
        self.assertEqual(p.rc, 0)
        # Check that there were no errors and that parts of the expected
        # progress message are written to stdout.
        self.assert_no_errors(p)
        self.assertIn('upload', p.stdout)
        self.assertIn('s3://%s/foo.txt' % bucket_name, p.stdout)

    def test_normal_output_quiet(self):
        bucket_name = _SHARED_BUCKET
        foo_txt = self.files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s/ --quiet' % (foo_txt, bucket_name))
        self.assertEqual(p.rc, 0)
        # Check that nothing was printed to stdout.
        self.assertEqual('', p.stdout)

    def test_normal_output_only_show_errors(self):
        bucket_name = _SHARED_BUCKET
        foo_txt = self.files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s/ --only-show-errors' % (foo_txt,
                                                          bucket_name))
        self.assertEqual(p.rc, 0)
        # Check that nothing was printed to stdout.
        self.assertEqual('', p.stdout)

    def test_normal_output_no_progress(self):
        bucket_name = _SHARED_BUCKET
        foo_txt = self.files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s/ --no-progress' % (foo_txt, bucket_name))
        self.assertEqual(p.rc, 0)
        # Ensure success message was printed
        self.assertIn('upload', p.stdout)
        self.assertIn('s3://%s/foo.txt' % bucket_name, p.stdout)
        self.assertNotIn('Completed ', p.stdout)
        self.assertNotIn('calculating', p.stdout)

    def test_error_output(self):
        foo_txt = self.files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws(f's3 cp {foo_txt} s3://{_NON_EXISTENT_BUCKET}/')
        # Check that there were errors and that the error was print to stderr.
        self.assertEqual(p.rc, 1)
        self.assertIn('upload failed', p.stderr)

    def test_error_ouput_quiet(self):
        foo_txt = self.files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws(f's3 cp {foo_txt} s3://{_NON_EXISTENT_BUCKET}/ --quiet')
        # Check that there were errors and that the error was not
        # print to stderr.
        self.assertEqual(p.rc, 1)
        self.assertEqual('', p.stderr)

    def test_error_ouput_only_show_errors(self):
        foo_txt = self.files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws(f's3 cp {foo_txt} s3://{_NON_EXISTENT_BUCKET}/ --only-show-errors')
        # Check that there were errors and that the error was print to stderr.
        self.assertEqual(p.rc, 1)
        self.assertIn('upload failed', p.stderr)

    def test_error_and_success_output_only_show_errors(self):
        # Make a bucket.
        bucket_name = _SHARED_BUCKET

        # Create one file.
        self.files.create_file('f', 'foo contents')

        # Create another file that has a slightly longer name than the first.
        self.files.create_file('bar.txt', 'bar contents')

        # Create a prefix that will cause the second created file to have a key
        # longer than 1024 bytes which is not allowed in s3.
        long_prefix = 'd' * 1022

        p = aws('s3 cp %s s3://%s/%s/ --only-show-errors --recursive'
                % (self.files.rootdir, bucket_name, long_prefix))

        # Check that there was at least one error.
        self.assertEqual(p.rc, 1)

        # Check that there was nothing written to stdout for successful upload.
        self.assertEqual('', p.stdout)

        # Check that the failed message showed up in stderr.
        self.assertIn('upload failed', p.stderr)

        # Ensure the expected successful key exists in the bucket.
        self.assertTrue(self.key_exists(bucket_name, long_prefix + '/f'))


class TestDryrun(BaseS3IntegrationTest):
    """
    This ensures that dryrun works.
    """
    def test_dryrun(self):
        bucket_name = _SHARED_BUCKET
        foo_txt = self.files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s/ --dryrun' % (foo_txt, bucket_name))
        self.assertEqual(p.rc, 0)
        self.assert_no_errors(p)
        self.assertTrue(self.key_not_exists(bucket_name, 'foo.txt'))

    def test_dryrun_large_files(self):
        bucket_name = _SHARED_BUCKET
        foo_txt = self.files.create_file('foo.txt', 'a' * 1024 * 1024 * 10)

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s/ --dryrun' % (foo_txt, bucket_name))
        self.assertEqual(p.rc, 0)
        self.assert_no_errors(p)
        self.assertTrue(
            self.key_not_exists(bucket_name, 'foo.txt'),
            "The key 'foo.txt' exists in S3. It looks like the --dryrun "
            "argument was not obeyed.")

    def test_dryrun_download_large_file(self):
        bucket_name = _SHARED_BUCKET
        full_path = self.files.create_file('largefile', 'a' * 1024 * 1024 * 10)
        with open(full_path, 'rb') as body:
            self.put_object(bucket_name, 'foo.txt', body)

        foo_txt = self.files.full_path('foo.txt')
        p = aws('s3 cp s3://%s/foo.txt %s --dryrun' % (bucket_name, foo_txt))
        self.assertEqual(p.rc, 0)
        self.assert_no_errors(p)
        self.assertFalse(
            os.path.exists(foo_txt),
            "The file 'foo.txt' exists locally. It looks like the --dryrun "
            "argument was not obeyed.")


@skip_if_windows('Memory tests only supported on mac/linux')
class TestMemoryUtilization(BaseS3IntegrationTest):
    # These tests verify the memory utilization and growth are what we expect.
    def extra_setup(self):
        self.num_threads = DEFAULTS['max_concurrent_requests']
        self.chunk_size = DEFAULTS['multipart_chunksize']
        expected_memory_usage = self.num_threads * self.chunk_size
        # margin for things like python VM overhead, botocore service
        # objects, etc.  1.5 is really generous, perhaps over time this can be
        # lowered.
        runtime_margin = 1.5
        self.max_mem_allowed = runtime_margin * expected_memory_usage

    def assert_max_memory_used(self, process, max_mem_allowed, full_command):
        peak_memory = max(process.memory_usage)
        if peak_memory > max_mem_allowed:
            failure_message = (
                'Exceeded max memory allowed (%s MB) for command '
                '"%s": %s MB' % (self.max_mem_allowed / 1024.0 / 1024.0,
                                 full_command,
                                 peak_memory / 1024.0 / 1024.0))
            self.fail(failure_message)

    @pytest.mark.slow
    def test_transfer_single_large_file(self):
        # 40MB will force a multipart upload.
        bucket_name = _SHARED_BUCKET
        file_contents = 'abcdabcd' * (1024 * 1024 * 10)
        foo_txt = self.files.create_file('foo.txt', file_contents)
        full_command = 's3 mv %s s3://%s/foo.txt' % (foo_txt, bucket_name)
        p = aws(full_command, collect_memory=True)
        self.assert_no_errors(p)
        self.assert_max_memory_used(p, self.max_mem_allowed, full_command)

        # Verify downloading it back down obeys memory utilization.
        download_full_command = 's3 mv s3://%s/foo.txt %s' % (
            bucket_name, foo_txt)
        p = aws(download_full_command, collect_memory=True)
        self.assert_no_errors(p)
        self.assert_max_memory_used(p, self.max_mem_allowed,
                                    download_full_command)

    # Some versions of RHEL allocate memory in a way where free'd memory isn't
    # given back to the OS.  We haven't seen behavior as bad as RHEL's to the
    # point where this test fails on other distros, so for now we're disabling
    # the test on RHEL until we come up with a better way to collect
    # memory usage.
    @pytest.mark.slow
    @unittest.skipIf(_running_on_rhel(),
                     'Streaming memory tests no supported on RHEL.')
    def test_stream_large_file(self):
        """
        This tests to ensure that streaming files for both uploads and
        downloads do not use too much memory.  Note that streaming uploads
        will use slightly more memory than usual but should not put the
        entire file into memory.
        """
        bucket_name = _SHARED_BUCKET

        # Create a 200 MB file that will be streamed
        num_mb = 200
        foo_txt = self.files.create_file('foo.txt', '')
        with open(foo_txt, 'wb') as f:
            for i in range(num_mb):
                f.write(b'a' * 1024 * 1024)

        # The current memory threshold is set at about the peak amount for
        # performing a streaming upload of a file larger than 100 MB. So
        # this maximum needs to be bumped up.  The maximum memory allowance
        # is increased by two chunksizes because that is the maximum
        # amount of chunks that will be queued while not being operated on
        # by a thread when performing a streaming multipart upload.
        max_mem_allowed = self.max_mem_allowed + 2 * self.chunk_size

        full_command = 's3 cp - s3://%s/foo.txt' % bucket_name
        with open(foo_txt, 'rb') as f:
            p = aws(full_command, input_file=f, collect_memory=True)
            self.assert_no_errors(p)
            self.assert_max_memory_used(p, max_mem_allowed, full_command)

        # Now perform a streaming download of the file.
        full_command = 's3 cp s3://%s/foo.txt - > %s' % (bucket_name, foo_txt)
        p = aws(full_command, collect_memory=True)
        self.assert_no_errors(p)
        # Use the usual bar for maximum memory usage since a streaming
        # download's memory usage should be comparable to non-streaming
        # transfers.
        self.assert_max_memory_used(p, self.max_mem_allowed, full_command)


class TestWebsiteConfiguration(BaseS3IntegrationTest):
    def test_create_website_index_configuration(self):
        bucket_name = self.create_bucket()
        # Supply only --index-document argument.
        full_command = 's3 website %s --index-document index.html' % \
            (bucket_name)
        p = aws(full_command)
        self.assertEqual(p.rc, 0)
        self.assert_no_errors(p)
        # Verify we have a bucket website configured.
        parsed = self.client.get_bucket_website(Bucket=bucket_name)
        self.assertEqual(parsed['IndexDocument']['Suffix'], 'index.html')
        self.assertNotIn('ErrorDocument', parsed)
        self.assertNotIn('RoutingRules', parsed)
        self.assertNotIn('RedirectAllRequestsTo', parsed)

    def test_create_website_index_and_error_configuration(self):
        bucket_name = self.create_bucket()
        # Supply both --index-document and --error-document arguments.
        p = aws('s3 website %s --index-document index.html '
                '--error-document error.html' % bucket_name)
        self.assertEqual(p.rc, 0)
        self.assert_no_errors(p)
        # Verify we have a bucket website configured.
        parsed = self.client.get_bucket_website(Bucket=bucket_name)
        self.assertEqual(parsed['IndexDocument']['Suffix'], 'index.html')
        self.assertEqual(parsed['ErrorDocument']['Key'], 'error.html')
        self.assertNotIn('RoutingRules', parsed)
        self.assertNotIn('RedirectAllRequestsTo', parsed)


class TestIncludeExcludeFilters(BaseS3IntegrationTest):
    def assert_no_files_would_be_uploaded(self, p):
        self.assert_no_errors(p)
        # There should be no output.
        self.assertEqual(p.stdout, '')
        self.assertEqual(p.stderr, '')

    def test_basic_exclude_filter_for_single_file(self):
        full_path = self.files.create_file('foo.txt', 'this is foo.txt')
        # With no exclude we should upload the file.
        p = aws('s3 cp %s s3://random-bucket-name/ --dryrun' % full_path)
        self.assert_no_errors(p)
        self.assertIn('(dryrun) upload:', p.stdout)

        p2 = aws("s3 cp %s s3://random-bucket-name/ --dryrun --exclude '*'"
                 % full_path)
        self.assert_no_files_would_be_uploaded(p2)

    def test_explicitly_exclude_single_file(self):
        full_path = self.files.create_file('foo.txt', 'this is foo.txt')
        p = aws('s3 cp %s s3://random-bucket-name/'
                ' --dryrun --exclude foo.txt'
                % full_path)
        self.assert_no_files_would_be_uploaded(p)

    def test_cwd_doesnt_matter(self):
        full_path = self.files.create_file('foo.txt', 'this is foo.txt')
        tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tempdir)
        with cd(tempdir):
            p = aws("s3 cp %s s3://random-bucket-name/ --dryrun --exclude '*'"
                    % full_path)
        self.assert_no_files_would_be_uploaded(p)

    def test_recursive_exclude(self):
        # create test/foo.txt
        nested_dir = os.path.join(self.files.rootdir, 'test')
        os.mkdir(nested_dir)
        self.files.create_file(os.path.join(nested_dir, 'foo.txt'),
                               contents='foo.txt contents')
        # Then create test-123.txt, test-321.txt, test.txt.
        self.files.create_file('test-123.txt', 'test-123.txt contents')
        self.files.create_file('test-321.txt', 'test-321.txt contents')
        self.files.create_file('test.txt', 'test.txt contents')
        # An --exclude test* should exclude everything here.
        p = aws("s3 cp %s s3://random-bucket-name/ --dryrun --exclude '*' "
                "--recursive" % self.files.rootdir)
        self.assert_no_files_would_be_uploaded(p)

        # We can include the test directory though.
        p = aws("s3 cp %s s3://random-bucket-name/ --dryrun "
                "--exclude '*' --include 'test/*' --recursive"
                % self.files.rootdir)
        self.assert_no_errors(p)
        self.assertRegex(p.stdout, r'\(dryrun\) upload:.*test/foo.txt.*')

    def test_s3_filtering(self):
        # Should behave the same as local file filtering.
        bucket_name = _SHARED_BUCKET
        self.put_object(bucket_name, key_name='foo.txt')
        self.put_object(bucket_name, key_name='bar.txt')
        self.put_object(bucket_name, key_name='baz.jpg')
        p = aws("s3 rm s3://%s/ --dryrun --exclude '*' --recursive"
                % bucket_name)
        self.assert_no_files_would_be_uploaded(p)

        p = aws(
            "s3 rm s3://%s/ --dryrun --exclude '*.jpg' --exclude '*.txt' "
            "--recursive" % bucket_name)
        self.assert_no_files_would_be_uploaded(p)

        p = aws("s3 rm s3://%s/ --dryrun --exclude '*.txt' --recursive"
                % bucket_name)
        self.assert_no_errors(p)
        self.assertRegex(p.stdout, r'\(dryrun\) delete:.*baz.jpg.*')
        self.assertNotIn(p.stdout, 'bar.txt')
        self.assertNotIn(p.stdout, 'foo.txt')

    def test_exclude_filter_with_delete(self):
        # Test for: https://github.com/aws/aws-cli/issues/778
        bucket_name = _SHARED_BUCKET
        self.files.create_file('foo.txt', 'contents')
        second = self.files.create_file('bar.py', 'contents')
        p = aws("s3 sync %s s3://%s/" % (self.files.rootdir, bucket_name))
        self.assert_no_errors(p)
        self.assertTrue(self.key_exists(bucket_name, key_name='bar.py'))
        os.remove(second)
        # We now have the same state as specified in the bug:
        # local           remote
        # -----           ------
        #
        # foo.txt         foo.txt
        #                 bar.py
        #
        # If we now run --exclude '*.py' --delete, then we should *not*
        # delete bar.py and the remote side.
        p = aws("s3 sync %s s3://%s/ --exclude '*.py' --delete" % (
            self.files.rootdir, bucket_name))
        self.assert_no_errors(p)
        self.assertTrue(
            self.key_exists(bucket_name, key_name='bar.py'),
            ("The --delete flag was not applied to the receiving "
             "end, the 'bar.py' file was deleted even though it"
             " was excluded."))

    def test_exclude_filter_with_relative_path(self):
        # Same test as test_exclude_filter_with_delete, except we don't
        # use an absolute path on the source dir.
        bucket_name = _SHARED_BUCKET
        self.files.create_file('foo.txt', 'contents')
        second = self.files.create_file('bar.py', 'contents')
        p = aws("s3 sync %s s3://%s/" % (self.files.rootdir, bucket_name))
        self.assert_no_errors(p)
        self.assertTrue(self.key_exists(bucket_name, key_name='bar.py'))
        os.remove(second)
        cwd = os.getcwd()
        try:
            os.chdir(self.files.rootdir)
            # Note how we're using "." for the source directory.
            p = aws("s3 sync . s3://%s/ --exclude '*.py' --delete"
                    % bucket_name)
        finally:
            os.chdir(cwd)
        self.assert_no_errors(p)
        self.assertTrue(
            self.key_exists(bucket_name, key_name='bar.py'),
            ("The --delete flag was not applied to the receiving "
             "end, the 'bar.py' file was deleted even though"
             " it was excluded."))

    def test_filter_s3_with_prefix(self):
        bucket_name = _SHARED_BUCKET
        self.put_object(bucket_name, key_name='temp/test')
        p = aws('s3 cp s3://%s/temp/ %s --recursive --exclude test --dryrun'
                % (bucket_name, self.files.rootdir))
        self.assert_no_files_would_be_uploaded(p)

    def test_filter_no_resync(self):
        # This specifically tests for the issue described here:
        # https://github.com/aws/aws-cli/issues/794
        bucket_name = _SHARED_BUCKET
        dir_name = os.path.join(self.files.rootdir, 'temp')
        self.files.create_file(os.path.join(dir_name, 'test.txt'),
                               contents='foo')
        # Sync a local directory to an s3 prefix.
        p = aws('s3 sync %s s3://%s/temp' % (dir_name, bucket_name))
        self.assert_no_errors(p)
        self.assertTrue(self.key_exists(bucket_name, key_name='temp/test.txt'))

        # Nothing should be synced down if filters are used.
        p = aws("s3 sync s3://%s/temp %s --exclude '*' --include test.txt"
                % (bucket_name, dir_name))
        self.assert_no_files_would_be_uploaded(p)


class TestFileWithSpaces(BaseS3IntegrationTest):
    def test_upload_download_file_with_spaces(self):
        bucket_name = _SHARED_BUCKET
        filename = self.files.create_file('with space.txt', 'contents')
        p = aws('s3 cp %s s3://%s/ --recursive' % (self.files.rootdir,
                                                   bucket_name))
        self.assert_no_errors(p)
        os.remove(filename)
        # Now download the file back down locally.
        p = aws('s3 cp s3://%s/ %s --recursive' % (bucket_name,
                                                   self.files.rootdir))
        self.assert_no_errors(p)
        self.assertEqual(os.listdir(self.files.rootdir)[0], 'with space.txt')

    def test_sync_file_with_spaces(self):
        bucket_name = _SHARED_BUCKET
        self.files.create_file('with space.txt',
                               'contents', mtime=time.time() - 300)
        p = aws('s3 sync %s s3://%s/' % (self.files.rootdir,
                                         bucket_name))
        self.assert_no_errors(p)
        time.sleep(1)
        # Now syncing again should *not* trigger any uploads (i.e we should
        # get nothing on stdout).
        p2 = aws('s3 sync %s s3://%s/' % (self.files.rootdir,
                                          bucket_name))
        self.assertEqual(p2.stdout, '')
        self.assertEqual(p2.stderr, '')
        self.assertEqual(p2.rc, 0)


class TestStreams(BaseS3IntegrationTest):
    def test_upload(self):
        """
        This tests uploading a small stream from stdin.
        """
        bucket_name = _SHARED_BUCKET
        p = aws('s3 cp - s3://%s/stream' % bucket_name,
                input_data=b'This is a test')
        self.assert_no_errors(p)
        self.assertTrue(self.key_exists(bucket_name, 'stream'))
        self.assertEqual(self.get_key_contents(bucket_name, 'stream'),
                         'This is a test')

    def test_unicode_upload(self):
        """
        This tests being able to upload unicode from stdin.
        """
        unicode_str = u'\u00e9 This is a test'
        byte_str = unicode_str.encode('utf-8')
        bucket_name = _SHARED_BUCKET
        p = aws('s3 cp - s3://%s/stream' % bucket_name,
                input_data=byte_str)
        self.assert_no_errors(p)
        self.assertTrue(self.key_exists(bucket_name, 'stream'))
        self.assertEqual(self.get_key_contents(bucket_name, 'stream'),
                         unicode_str)

    @pytest.mark.slow
    def test_multipart_upload(self):
        """
        This tests the ability to multipart upload streams from stdin.
        The data has some unicode in it to avoid having to do a separate
        multipart upload test just for unicode.
        """
        bucket_name = _SHARED_BUCKET
        data = u'\u00e9bcd' * (1024 * 1024 * 10)
        data_encoded = data.encode('utf-8')
        p = aws('s3 cp - s3://%s/stream' % bucket_name,
                input_data=data_encoded)
        self.assert_no_errors(p)
        self.assertTrue(self.key_exists(bucket_name, 'stream'))
        self.assert_key_contents_equal(bucket_name, 'stream', data)

    def test_download(self):
        """
        This tests downloading a small stream from stdout.
        """
        bucket_name = _SHARED_BUCKET
        p = aws('s3 cp - s3://%s/stream' % bucket_name,
                input_data=b'This is a test')
        self.assert_no_errors(p)

        p = aws('s3 cp s3://%s/stream -' % bucket_name)
        self.assert_no_errors(p)
        self.assertEqual(p.stdout, 'This is a test')

    def test_unicode_download(self):
        """
        This tests downloading a small unicode stream from stdout.
        """
        bucket_name = _SHARED_BUCKET

        data = u'\u00e9 This is a test'
        data_encoded = data.encode('utf-8')
        p = aws('s3 cp - s3://%s/stream' % bucket_name,
                input_data=data_encoded)
        self.assert_no_errors(p)

        # Downloading the unicode stream to standard out.
        p = aws('s3 cp s3://%s/stream -' % bucket_name)
        self.assert_no_errors(p)
        self.assertEqual(p.stdout, data_encoded.decode(get_stdout_encoding()))

    @pytest.mark.slow
    def test_multipart_download(self):
        """
        This tests the ability to multipart download streams to stdout.
        The data has some unicode in it to avoid having to do a separate
        multipart download test just for unicode.
        """
        bucket_name = _SHARED_BUCKET

        # First lets upload some data via streaming since
        # its faster and we do not have to write to a file!
        data = u'\u00e9bcd' * (1024 * 1024 * 10)
        data_encoded = data.encode('utf-8')
        p = aws('s3 cp - s3://%s/stream' % bucket_name,
                input_data=data_encoded)

        # Download the unicode stream to standard out.
        p = aws('s3 cp s3://%s/stream -' % bucket_name)
        self.assert_no_errors(p)
        self.assertEqual(p.stdout, data_encoded.decode(get_stdout_encoding()))


class TestLSWithProfile(BaseS3IntegrationTest):
    def extra_setup(self):
        self.config_file = os.path.join(self.files.rootdir, 'tmpconfig')
        with open(self.config_file, 'w') as f:
            creds = self.session.get_credentials()
            f.write(
                "[profile testprofile]\n"
                "aws_access_key_id=%s\n"
                "aws_secret_access_key=%s\n" % (
                    creds.access_key,
                    creds.secret_key)
            )
            if creds.token is not None:
                f.write("aws_session_token=%s\n" % creds.token)

    def test_can_ls_with_profile(self):
        env_vars = os.environ.copy()
        env_vars['AWS_CONFIG_FILE'] = self.config_file
        p = aws('s3 ls s3:// --profile testprofile', env_vars=env_vars)
        self.assert_no_errors(p)


class TestNoSignRequests(BaseS3IntegrationTest):
    def test_no_sign_request(self):
        bucket_name = _SHARED_BUCKET
        self.put_object(bucket_name, 'foo', contents='bar',
                        extra_args={'ACL': 'public-read-write'})
        env_vars = os.environ.copy()
        env_vars['AWS_ACCESS_KEY_ID'] = 'foo'
        env_vars['AWS_SECRET_ACCESS_KEY'] = 'bar'
        p = aws('s3 cp s3://%s/foo %s/ --region %s' %
                (bucket_name, self.files.rootdir, self.region),
                env_vars=env_vars)
        # Should have credential issues
        self.assertEqual(p.rc, 1)

        p = aws('s3 cp s3://%s/foo %s/ --region %s --no-sign-request' %
                (bucket_name, self.files.rootdir, self.region),
                env_vars=env_vars)
        # Should be able to download the file when not signing the request.
        self.assert_no_errors(p)


class TestHonorsEndpointUrl(BaseS3IntegrationTest):
    def test_verify_endpoint_url_is_used(self):
        # We're going to verify this indirectly by looking at the
        # debug logs.  The endpoint url we specify should be in the
        # debug logs, and the endpoint url that botocore would have
        # used if we didn't provide the endpoint-url should not
        # be in the debug logs.  The other alternative is to actually
        # watch what connections are made in the process, which is not
        # easy.
        p = aws('s3 ls s3://dnscompat/ '
                '--endpoint-url http://localhost:51515 '
                '--debug')
        debug_logs = p.stderr
        original_hostname = 'dnscompat.s3.amazonaws.com'
        expected = 'localhost'
        self.assertNotIn(original_hostname, debug_logs,
                         '--endpoint-url is being ignored in s3 commands.')
        self.assertIn(expected, debug_logs)


class TestSSERelatedParams(BaseS3IntegrationTest):
    def download_and_assert_kms_object_integrity(self, bucket, key, contents):
        self.wait_until_key_exists(bucket, key)
        # Ensure the kms object can be download it by downloading it
        # with --sse aws:kms is enabled to ensure sigv4 is used on the
        # download, as it is required for kms.
        download_filename = os.path.join(self.files.rootdir, 'tmp', key)
        p = aws('s3 cp s3://%s/%s %s --sse aws:kms' % (
            bucket, key, download_filename))
        self.assert_no_errors(p)

        self.assertTrue(os.path.isfile(download_filename))
        with open(download_filename, 'r') as f:
            self.assertEqual(f.read(), contents)

    def test_sse_upload(self):
        bucket = _SHARED_BUCKET
        key = 'foo.txt'
        contents = 'contents'
        file_name = self.files.create_file(key, contents)

        # Upload the file using AES256
        p = aws('s3 cp %s s3://%s/%s --sse AES256' % (file_name, bucket, key))
        self.assert_no_errors(p)

        # Ensure the file was uploaded correctly
        self.assert_key_contents_equal(bucket, key, contents)

    def test_large_file_sse_upload(self):
        bucket = _SHARED_BUCKET
        key = 'foo.txt'
        contents = 'a' * (10 * (1024 * 1024))
        file_name = self.files.create_file(key, contents)

        # Upload the file using AES256
        p = aws('s3 cp %s s3://%s/%s --sse AES256' % (file_name, bucket, key))
        self.assert_no_errors(p)

        # Ensure the file was uploaded correctly
        self.assert_key_contents_equal(bucket, key, contents)

    def test_sse_with_kms_upload(self):
        bucket = _SHARED_BUCKET
        key = 'foo.txt'
        contents = 'contents'
        file_name = self.files.create_file(key, contents)

        # Upload the file using KMS
        p = aws('s3 cp %s s3://%s/%s --sse aws:kms' % (file_name, bucket, key))
        self.assert_no_errors(p)

        self.download_and_assert_kms_object_integrity(bucket, key, contents)

    def test_large_file_sse_kms_upload(self):
        bucket = _SHARED_BUCKET
        key = 'foo.txt'
        contents = 'a' * (10 * (1024 * 1024))
        file_name = self.files.create_file(key, contents)

        # Upload the file using KMS
        p = aws('s3 cp %s s3://%s/%s --sse aws:kms' % (file_name, bucket, key))
        self.assert_no_errors(p)

        self.download_and_assert_kms_object_integrity(bucket, key, contents)

    def test_sse_copy(self):
        bucket = _SHARED_BUCKET
        key = 'foo.txt'
        new_key = 'bar.txt'
        contents = 'contents'
        self.put_object(bucket, key, contents)

        # Copy the file using AES256
        p = aws('s3 cp s3://%s/%s s3://%s/%s --sse AES256' % (
            bucket, key, bucket, new_key))
        self.assert_no_errors(p)

        # Ensure the file was copied correctly
        self.assert_key_contents_equal(bucket, new_key, contents)

    def test_large_file_sse_copy(self):
        bucket = _SHARED_BUCKET
        key = 'foo.txt'
        new_key = 'bar.txt'
        contents = 'a' * (10 * (1024 * 1024))

        # This is a little faster and more efficient than
        # calling self.put_object()
        file_name = self.files.create_file(key, contents)
        p = aws('s3 cp %s s3://%s/%s' % (file_name, bucket, key))
        self.assert_no_errors(p)

        # Copy the file using AES256
        p = aws('s3 cp s3://%s/%s s3://%s/%s --sse AES256' % (
            bucket, key, bucket, new_key))
        self.assert_no_errors(p)

        # Ensure the file was copied correctly
        self.assert_key_contents_equal(bucket, new_key, contents)

    def test_sse_kms_copy(self):
        bucket = _SHARED_BUCKET
        key = 'foo.txt'
        new_key = 'bar.txt'
        contents = 'contents'
        self.put_object(bucket, key, contents)

        # Copy the file using KMS
        p = aws('s3 cp s3://%s/%s s3://%s/%s --sse aws:kms' % (
            bucket, key, bucket, new_key))
        self.assert_no_errors(p)
        self.download_and_assert_kms_object_integrity(bucket, key, contents)

    def test_large_file_sse_kms_copy(self):
        bucket = _SHARED_BUCKET
        key = 'foo.txt'
        new_key = 'bar.txt'
        contents = 'a' * (10 * (1024 * 1024))

        # This is a little faster and more efficient than
        # calling self.put_object()
        file_name = self.files.create_file(key, contents)
        p = aws('s3 cp %s s3://%s/%s' % (file_name, bucket, key))
        self.assert_no_errors(p)

        # Copy the file using KMS
        p = aws('s3 cp s3://%s/%s s3://%s/%s --sse aws:kms' % (
            bucket, key, bucket, new_key))
        self.assert_no_errors(p)
        self.download_and_assert_kms_object_integrity(bucket, key, contents)

    def test_smoke_sync_sse(self):
        bucket = _SHARED_BUCKET
        key = 'foo.txt'
        contents = 'contents'
        file_name = self.files.create_file(key, contents)

        # Upload sync
        p = aws('s3 sync %s s3://%s/foo/ --sse AES256' % (
            self.files.rootdir, bucket))
        self.assert_no_errors(p)
        self.wait_until_key_exists(bucket, 'foo/foo.txt')

        # Copy sync
        p = aws('s3 sync s3://%s/foo/ s3://%s/bar/ --sse AES256' % (
            bucket, bucket))
        self.assert_no_errors(p)
        self.wait_until_key_exists(bucket, 'bar/foo.txt')

        # Remove the original file
        os.remove(file_name)

        # Download sync
        p = aws('s3 sync s3://%s/bar/ %s --sse AES256' % (
            bucket, self.files.rootdir))
        self.assert_no_errors(p)

        self.assertTrue(os.path.isfile(file_name))
        with open(file_name, 'r') as f:
            self.assertEqual(f.read(), contents)

    def test_smoke_sync_sse_kms(self):
        bucket = _SHARED_BUCKET
        key = 'foo.txt'
        contents = 'contents'
        file_name = self.files.create_file(key, contents)

        # Upload sync
        p = aws('s3 sync %s s3://%s/foo/ --sse aws:kms' % (
            self.files.rootdir, bucket))
        self.assert_no_errors(p)

        # Copy sync
        p = aws('s3 sync s3://%s/foo/ s3://%s/bar/ --sse aws:kms' % (
            bucket, bucket))
        self.assert_no_errors(p)

        # Remove the original file
        os.remove(file_name)

        # Download sync
        p = aws('s3 sync s3://%s/bar/ %s --sse aws:kms' % (
            bucket, self.files.rootdir))
        self.assert_no_errors(p)

        self.assertTrue(os.path.isfile(file_name))
        with open(file_name, 'r') as f:
            self.assertEqual(f.read(), contents)


class TestSSECRelatedParams(BaseS3IntegrationTest):
    def setUp(self):
        super(TestSSECRelatedParams, self).setUp()
        self.encrypt_key = 'a' * 32
        self.other_encrypt_key = 'b' * 32
        self.bucket = _SHARED_BUCKET

    def download_and_assert_sse_c_object_integrity(
            self, bucket, key, encrypt_key, contents):
        self.wait_until_key_exists(bucket, key,
                                   {'SSECustomerKey': encrypt_key,
                                    'SSECustomerAlgorithm': 'AES256'})
        download_filename = os.path.join(self.files.rootdir, 'tmp', key)
        p = aws('s3 cp s3://%s/%s %s --sse-c AES256 --sse-c-key %s' % (
            bucket, key, download_filename, encrypt_key))
        self.assert_no_errors(p)

        self.assertTrue(os.path.isfile(download_filename))
        with open(download_filename, 'r') as f:
            self.assertEqual(f.read(), contents)

    def test_sse_c_upload_and_download(self):
        key = 'foo.txt'
        contents = 'contents'
        file_name = self.files.create_file(key, contents)

        # Upload the file using SSE-C
        p = aws('s3 cp %s s3://%s --sse-c AES256 --sse-c-key %s' % (
            file_name, self.bucket, self.encrypt_key))
        self.assert_no_errors(p)

        self.download_and_assert_sse_c_object_integrity(
            self.bucket, key, self.encrypt_key, contents)

    def test_can_delete_single_sse_c_object(self):
        key = 'foo.txt'
        contents = 'contents'
        self.put_object(
            self.bucket, key, contents,
            extra_args={
                'SSECustomerKey': self.encrypt_key,
                'SSECustomerAlgorithm': 'AES256'
            }
        )
        p = aws('s3 rm s3://%s/%s' % (self.bucket, key))
        self.assert_no_errors(p)
        self.assertFalse(self.key_exists(self.bucket, key))

    def test_sse_c_upload_and_download_large_file(self):
        key = 'foo.txt'
        contents = 'a' * (10 * (1024 * 1024))
        file_name = self.files.create_file(key, contents)

        # Upload the file using SSE-C
        p = aws('s3 cp %s s3://%s --sse-c AES256 --sse-c-key %s' % (
            file_name, self.bucket, self.encrypt_key))
        self.assert_no_errors(p)

        self.download_and_assert_sse_c_object_integrity(
            self.bucket, key, self.encrypt_key, contents)

    def test_sse_c_copy(self):
        key = 'foo.txt'
        new_key = 'bar.txt'
        contents = 'contents'
        file_name = self.files.create_file(key, contents)

        # Upload the file using SSE-C
        p = aws('s3 cp %s s3://%s --sse-c AES256 --sse-c-key %s' % (
            file_name, self.bucket, self.encrypt_key))
        self.assert_no_errors(p)

        # Copy the file using SSE-C and a new encryption key
        p = aws(
            's3 cp s3://%s/%s s3://%s/%s --sse-c AES256 --sse-c-key %s '
            '--sse-c-copy-source AES256 --sse-c-copy-source-key %s' % (
                self.bucket, key, self.bucket, new_key, self.other_encrypt_key,
                self.encrypt_key))
        self.assert_no_errors(p)
        self.download_and_assert_sse_c_object_integrity(
            self.bucket, new_key, self.other_encrypt_key, contents)

    def test_sse_c_copy_large_file(self):
        key = 'foo.txt'
        new_key = 'bar.txt'
        contents = 'a' * (10 * (1024 * 1024))
        file_name = self.files.create_file(key, contents)

        # Upload the file using SSE-C
        p = aws('s3 cp %s s3://%s --sse-c AES256 --sse-c-key %s' % (
            file_name, self.bucket, self.encrypt_key))
        self.assert_no_errors(p)

        # Copy the file using SSE-C and a new encryption key
        p = aws(
            's3 cp s3://%s/%s s3://%s/%s --sse-c AES256 --sse-c-key %s '
            '--sse-c-copy-source AES256 --sse-c-copy-source-key %s' % (
                self.bucket, key, self.bucket, new_key, self.other_encrypt_key,
                self.encrypt_key))
        self.assert_no_errors(p)
        self.download_and_assert_sse_c_object_integrity(
            self.bucket, new_key, self.other_encrypt_key, contents)

    def test_smoke_sync_sse_c(self):
        key = 'foo.txt'
        contents = 'contents'
        file_name = self.files.create_file(key, contents)

        # Upload sync
        p = aws('s3 sync %s s3://%s/foo/ --sse-c AES256 --sse-c-key %s' % (
            self.files.rootdir, self.bucket, self.encrypt_key))
        self.assert_no_errors(p)

        # Copy sync
        p = aws('s3 sync s3://%s/foo/ s3://%s/bar/ --sse-c AES256 '
                '--sse-c-key %s --sse-c-copy-source AES256 '
                '--sse-c-copy-source-key %s' % (
                    self.bucket, self.bucket, self.other_encrypt_key,
                    self.encrypt_key))
        self.assert_no_errors(p)

        # Remove the original file
        os.remove(file_name)

        # Download sync
        p = aws('s3 sync s3://%s/bar/ %s --sse-c AES256 --sse-c-key %s' % (
            self.bucket, self.files.rootdir, self.other_encrypt_key))
        self.assert_no_errors(p)

        self.assertTrue(os.path.isfile(file_name))
        with open(file_name, 'r') as f:
            self.assertEqual(f.read(), contents)


class TestPresignCommand(BaseS3IntegrationTest):

    def test_can_retrieve_presigned_url(self):
        bucket_name = _SHARED_BUCKET
        original_contents = b'this is foo.txt'
        self.put_object(bucket_name, 'foo.txt', original_contents)
        p = aws('s3 presign s3://%s/foo.txt' % (bucket_name,))
        self.assert_no_errors(p)
        url = p.stdout.strip()
        contents = urlopen(url).read()
        self.assertEqual(contents, original_contents)
