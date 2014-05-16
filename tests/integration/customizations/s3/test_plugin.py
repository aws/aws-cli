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
from tests import unittest
import os
import random
import platform
import contextlib
import time
import signal

import botocore.session
import six

from tests.integration import aws
from tests.unit.customizations.s3 import create_bucket as _create_bucket
from tests.unit import FileCreator
from awscli.customizations.s3 import constants


@contextlib.contextmanager
def cd(directory):
    original = os.getcwd()
    try:
        os.chdir(directory)
        yield
    finally:
        os.chdir(original)


class BaseS3CLICommand(unittest.TestCase):
    """Base class for aws s3 command.

    This contains convenience functions to make writing these tests easier
    and more streamlined.

    """
    def setUp(self):
        self.files = FileCreator()
        self.session = botocore.session.get_session()
        self.service = self.session.get_service('s3')
        self.endpoint = self.service.get_endpoint('us-east-1')
        self.extra_setup()

    def extra_setup(self):
        # Subclasses can use this to define extra setup steps.
        pass

    def tearDown(self):
        self.files.remove_all()
        self.extra_teardown()

    def extra_teardown(self):
        # Subclasses can use this to define extra teardown steps.
        pass

    def assert_key_contents_equal(self, bucket, key, expected_contents):
        if isinstance(expected_contents, six.BytesIO):
            expected_contents = expected_contents.getvalue().decode('utf-8')
        actual_contents = self.get_key_contents(bucket, key)
        # The contents can be huge so we try to give helpful error messages
        # without necessarily printing the actual contents.
        self.assertEqual(len(actual_contents), len(expected_contents))
        if actual_contents != expected_contents:
            self.fail("Contents for %s/%s do not match (but they "
                      "have the same length)" % (bucket, key))

    def create_bucket(self):
        bucket_name = _create_bucket(self.session)
        self.addCleanup(self.delete_bucket, bucket_name)
        return bucket_name

    def put_object(self, bucket_name, key_name, contents=''):
        operation = self.service.get_operation('PutObject')
        http = operation.call(self.endpoint, bucket=bucket_name,
                              key=key_name, body=contents)[0]
        self.assertEqual(http.status_code, 200)
        self.addCleanup(self.delete_key, bucket_name, key_name)

    def delete_bucket(self, bucket_name):
        self.remove_all_objects(bucket_name)
        operation = self.service.get_operation('DeleteBucket')
        response = operation.call(self.endpoint, bucket=bucket_name)[0]
        self.assertEqual(response.status_code, 204, response.content)

    def remove_all_objects(self, bucket_name):
        operation = self.service.get_operation('ListObjects')
        pages = operation.paginate(self.endpoint, bucket=bucket_name)
        parsed = pages.build_full_result()
        key_names = [obj['Key'] for obj in parsed['Contents']]
        for key_name in key_names:
            self.delete_key(bucket_name, key_name)

    def delete_key(self, bucket_name, key_name):
        operation = self.service.get_operation('DeleteObject')
        response = operation.call(self.endpoint, bucket=bucket_name,
                                  key=key_name)[0]
        self.assertEqual(response.status_code, 204)

    def get_key_contents(self, bucket_name, key_name):
        operation = self.service.get_operation('GetObject')
        http, parsed = operation.call(
            self.endpoint, bucket=bucket_name, key=key_name)
        self.assertEqual(http.status_code, 200)
        return parsed['Body'].read().decode('utf-8')

    def key_exists(self, bucket_name, key_name):
        operation = self.service.get_operation('HeadObject')
        http, parsed = operation.call(
            self.endpoint, bucket=bucket_name, key=key_name)
        return http.status_code == 200

    def list_buckets(self):
        operation = self.service.get_operation('ListBuckets')
        http, parsed = operation.call(self.endpoint)
        self.assertEqual(http.status_code, 200)
        return parsed['Buckets']

    def content_type_for_key(self, bucket_name, key_name):
        operation = self.service.get_operation('HeadObject')
        http, parsed = operation.call(
            self.endpoint, bucket=bucket_name, key=key_name)
        self.assertEqual(http.status_code, 200)
        return parsed['ContentType']

    def assert_no_errors(self, p):
        self.assertEqual(
            p.rc, 0,
            "Non zero rc (%s) received: %s" % (p.rc, p.stdout + p.stderr))
        self.assertNotIn("Error:", p.stdout)
        self.assertNotIn("failed:", p.stdout)
        self.assertNotIn("client error", p.stdout)
        self.assertNotIn("server error", p.stdout)


class TestMoveCommand(BaseS3CLICommand):

    def test_mv_local_to_s3(self):
        bucket_name = self.create_bucket()
        full_path = self.files.create_file('foo.txt', 'this is foo.txt')
        p = aws('s3 mv %s s3://%s/foo.txt' % (full_path,
                                              bucket_name))
        self.assert_no_errors(p)
        # When we move an object, the local file is gone:
        self.assertTrue(not os.path.exists(full_path))
        # And now resides in s3.
        self.assert_key_contents_equal(bucket_name, 'foo.txt', 'this is foo.txt')

    def test_mv_s3_to_local(self):
        bucket_name = self.create_bucket()
        self.put_object(bucket_name, 'foo.txt', 'this is foo.txt')
        full_path = self.files.full_path('foo.txt')
        self.assertTrue(self.key_exists(bucket_name, key_name='foo.txt'))
        p = aws('s3 mv s3://%s/foo.txt %s' % (bucket_name, full_path))
        self.assert_no_errors(p)
        self.assertTrue(os.path.exists(full_path))
        with open(full_path, 'r') as f:
            self.assertEqual(f.read(), 'this is foo.txt')
        # The s3 file should not be there anymore.
        self.assertTrue(not self.key_exists(bucket_name, key_name='foo.txt'))

    def test_mv_s3_to_s3(self):
        from_bucket = self.create_bucket()
        to_bucket = self.create_bucket()
        self.put_object(from_bucket, 'foo.txt', 'this is foo.txt')

        p = aws('s3 mv s3://%s/foo.txt s3://%s/foo.txt' % (from_bucket,
                                                           to_bucket))
        self.assert_no_errors(p)
        contents = self.get_key_contents(to_bucket, 'foo.txt')
        self.assertEqual(contents, 'this is foo.txt')
        # And verify that the object no longer exists in the from_bucket.
        self.assertTrue(not self.key_exists(from_bucket, key_name='foo.txt'))

    def test_mv_s3_to_s3_multipart(self):
        from_bucket = self.create_bucket()
        to_bucket = self.create_bucket()
        file_contents = six.BytesIO(b'abcd' * (1024 * 1024 * 10))
        self.put_object(from_bucket, 'foo.txt', file_contents)

        p = aws('s3 mv s3://%s/foo.txt s3://%s/foo.txt' % (from_bucket,
                                                           to_bucket))
        self.assert_no_errors(p)
        self.assert_key_contents_equal(to_bucket, 'foo.txt', file_contents)
        # And verify that the object no longer exists in the from_bucket.
        self.assertTrue(not self.key_exists(from_bucket, key_name='foo.txt'))

    def test_mv_s3_to_s3_multipart_recursive(self):
        from_bucket = self.create_bucket()
        to_bucket = self.create_bucket()

        large_file_contents = six.BytesIO(b'abcd' * (1024 * 1024 * 10))
        small_file_contents = 'small file contents'
        self.put_object(from_bucket, 'largefile', large_file_contents)
        self.put_object(from_bucket, 'smallfile', small_file_contents)

        p = aws('s3 mv s3://%s/ s3://%s/ --recursive' % (from_bucket,
                                                         to_bucket))
        self.assert_no_errors(p)
        # Nothing's in the from_bucket.
        self.assertTrue(not self.key_exists(from_bucket, key_name='largefile'))
        self.assertTrue(not self.key_exists(from_bucket, key_name='smallfile'))

        # And both files are in the to_bucket.
        self.assertTrue(self.key_exists(to_bucket, key_name='largefile'))
        self.assertTrue(self.key_exists(to_bucket, key_name='smallfile'))

        # And the contents are what we expect.
        self.assert_key_contents_equal(to_bucket, 'smallfile',
                                       small_file_contents)
        self.assert_key_contents_equal(to_bucket, 'largefile',
                                       large_file_contents)

    def test_mv_with_large_file(self):
        bucket_name = self.create_bucket()
        # 40MB will force a multipart upload.
        file_contents = six.BytesIO(b'abcd' * (1024 * 1024 * 10))
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
        self.assertEqual(os.path.getsize(foo_txt), len(file_contents.getvalue()))

    def test_mv_to_nonexistent_bucket(self):
        full_path = self.files.create_file('foo.txt', 'this is foo.txt')
        p = aws('s3 mv %s s3://bad-noexist-13143242/foo.txt' % (full_path,))
        self.assertEqual(p.rc, 1)


class TestRm(BaseS3CLICommand):
    @unittest.skipIf(platform.system() not in ['Darwin', 'Linux'],
                    'Newline in filename test not valid on windows.')
    # Windows won't let you do this.  You'll get:
    # [Errno 22] invalid mode ('w') or filename: # 'c:\\windows\\temp\\tmp0fv8uu\\foo\r.txt'
    def test_rm_with_newlines(self):
        bucket_name = self.create_bucket()

        # Note the carriage return in the key name.
        foo_txt = self.files.create_file('foo\r.txt', 'this is foo.txt')
        p = aws('s3 cp %s s3://%s/foo\r.txt' % (foo_txt, bucket_name))
        self.assert_no_errors(p)

        # Make sure object is in bucket.
        self.assertTrue(self.key_exists(bucket_name, key_name='foo\r.txt'))

        # Then delete the file.
        p = aws('s3 rm s3://%s/ --recursive' % (bucket_name,))

        # And verify it's gone.
        self.assertFalse(self.key_exists(bucket_name, key_name='foo\r.txt'))


class TestCp(BaseS3CLICommand):

    def test_cp_to_and_from_s3(self):
        # This tests the ability to put a single file in s3
        # move it to a different bucket.
        # and download the file locally
        bucket_name = self.create_bucket()

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

    def test_cp_without_trailing_slash(self):
        # There's a unit test for this, but we still want to verify this
        # with an integration test.
        bucket_name = self.create_bucket()

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

    def test_cp_s3_s3_multipart(self):
        from_bucket = self.create_bucket()
        to_bucket = self.create_bucket()
        file_contents = six.BytesIO(b'abcd' * (1024 * 1024 * 10))
        self.put_object(from_bucket, 'foo.txt', file_contents)

        p = aws('s3 cp s3://%s/foo.txt s3://%s/foo.txt' % (from_bucket, to_bucket))
        self.assert_no_errors(p)
        self.assert_key_contents_equal(to_bucket, 'foo.txt', file_contents)
        self.assertTrue(self.key_exists(from_bucket, key_name='foo.txt'))

    def test_guess_mime_type(self):
        bucket_name = self.create_bucket()
        bar_png = self.files.create_file('bar.jpeg', 'fake png image')
        p = aws('s3 cp %s s3://%s/bar.jpeg' % (bar_png, bucket_name))
        self.assert_no_errors(p)

        # We should have correctly guessed the content type based on the
        # filename extension.
        self.assertEqual(
            self.content_type_for_key(bucket_name, key_name='bar.jpeg'),
            'image/jpeg')

    def test_download_large_file(self):
        # This will force a multipart download.
        bucket_name = self.create_bucket()
        foo_contents = six.BytesIO(b'abcd' * (1024 * 1024 * 10))
        self.put_object(bucket_name, key_name='foo.txt', contents=foo_contents)
        local_foo_txt = self.files.full_path('foo.txt')
        p = aws('s3 cp s3://%s/foo.txt %s' % (bucket_name, local_foo_txt))
        self.assert_no_errors(p)
        self.assertEqual(os.path.getsize(local_foo_txt),
                         len(foo_contents.getvalue()))

    @unittest.skipIf(platform.system() not in ['Darwin', 'Linux'],
                    'SIGINT not supported on Windows.')
    def test_download_ctrl_c_does_not_hang(self):
        bucket_name = self.create_bucket()
        foo_contents = six.BytesIO(b'abcd' * (1024 * 1024 * 20))
        self.put_object(bucket_name, key_name='foo.txt', contents=foo_contents)
        local_foo_txt = self.files.full_path('foo.txt')
        process = aws('s3 cp s3://%s/foo.txt %s' % (bucket_name, local_foo_txt), wait_for_finish=False)
        # Give it some time to start up and enter it's main task loop.
        time.sleep(1)
        # The process has 30 seconds to finish after being sent a Ctrl+C,
        # otherwise the test fails.
        process.send_signal(signal.SIGINT)
        deadline = time.time() + 30
        while time.time() < deadline:
            rc = process.poll()
            if rc is not None:
                break
        else:
            process.kill()
            self.fail("CLI did not exist within 30 seconds of receiving a Ctrl+C")
        # A Ctrl+C should have a non-zero RC.  We either caught the process in
        # its main polling loop (rc=1), or it was successfully terminated by
        # the SIGINT (rc=-2).
        self.assertIn(process.returncode, [1, -2])

    def test_cp_to_nonexistent_bucket(self):
        foo_txt = self.files.create_file('foo.txt', 'this is foo.txt')
        p = aws('s3 cp %s s3://noexist-bucket-foo-bar123/foo.txt' % (foo_txt,))
        self.assertEqual(p.rc, 1)

    def test_cp_empty_file(self):
        bucket_name = self.create_bucket()
        foo_txt = self.files.create_file('foo.txt', contents='')
        p = aws('s3 cp %s s3://%s/' % (foo_txt, bucket_name))
        self.assertEqual(p.rc, 0)
        self.assertNotIn('failed', p.stderr)
        self.assertTrue(self.key_exists(bucket_name, 'foo.txt'))

    def test_download_non_existent_key(self):
        p = aws('s3 cp s3://jasoidfjasdjfasdofijasdf/foo.txt foo.txt')
        self.assertEqual(p.rc, 1)
        expected_err_msg = (
            'A client error (NoSuchKey) occurred when calling the '
            'HeadObject operation: Key "foo.txt" does not exist')
        self.assertIn(expected_err_msg, p.stdout)


class TestSync(BaseS3CLICommand):
    def test_sync_with_plus_chars(self):
        # 1. Create > 1000 files with '+' in the filename.
        # 2. Sync up to s3.
        # 3. Sync up to s3
        # 4. Verify nothing was synced up down from s3 in step 3.
        bucket_name = self.create_bucket()
        filenames = []
        for i in range(2000):
            # Create a file with a space char and a '+' char in the filename.
            filenames.append(self.files.create_file('foo +%06d' % i, contents=''))
        p = aws('s3 sync %s s3://%s/' % (self.files.rootdir, bucket_name))
        self.assert_no_errors(p)
        time.sleep(1)
        p2 = aws('s3 sync %s s3://%s/' % (self.files.rootdir, bucket_name))
        self.assertNotIn('upload:', p2.stdout)
        self.assertEqual('', p2.stdout)

    def test_sync_to_from_s3(self):
        bucket_name = self.create_bucket()
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
        bucket_name = self.create_bucket()
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
        bucket_name = self.create_bucket()
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


@unittest.skipIf(platform.system() not in ['Darwin', 'Linux'],
                 'Symlink tests only supported on mac/linux')
class TestBadSymlinks(BaseS3CLICommand):
    def test_bad_symlink_stops_sync_process(self):
        bucket_name = self.create_bucket()
        nested_dir = os.path.join(self.files.rootdir, 'realfiles')
        os.mkdir(nested_dir)
        full_path = self.files.create_file(os.path.join(nested_dir, 'foo.txt'),
                                           contents='foo.txt contents')
        symlink_dir = os.path.join(self.files.rootdir, 'symlinkdir')
        os.mkdir(symlink_dir)
        os.symlink(full_path, os.path.join(symlink_dir, 'a-goodsymlink'))
        os.symlink('non-existent-file', os.path.join(symlink_dir, 'b-badsymlink'))
        os.symlink(full_path, os.path.join(symlink_dir, 'c-goodsymlink'))
        p = aws('s3 sync %s s3://%s/' % (symlink_dir, bucket_name))
        self.assertEqual(p.rc, 1, p.stdout)
        self.assertIn('[Errno 2] No such file or directory', p.stdout)


class TestUnicode(BaseS3CLICommand):
    """
    The purpose of these tests are to ensure that the commands can handle
    unicode characters in both keyname and from those generated for both
    uploading and downloading files.
    """

    def test_cp(self):
        bucket_name = self.create_bucket()
        local_example1_txt = self.files.create_file(u'\u00e9xample.txt', 'example1 contents')
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
        bucket_name = self.create_bucket()
        local_example1_txt = self.files.create_file(u'\u00e9xample.txt', 'example1 contents')
        local_example2_txt = self.files.create_file(u'\u00e9xample2.txt', 'example2 contents')
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


class TestLs(BaseS3CLICommand):
    """
    This tests using the ``ls`` command.
    """
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
        p = aws('s3 ls s3://foobara99842u4wbts829381')
        self.assertEqual(p.rc, 255)
        self.assertIn(
            ('A client error (NoSuchBucket) occurred when calling the '
             'ListObjects operation: The specified bucket does not exist'),
            p.stderr)
        # There should be no stdout if we can't find the bucket.
        self.assertEqual(p.stdout, '')

    def test_ls_with_prefix(self):
        bucket_name = self.create_bucket()
        self.put_object(bucket_name, 'foo.txt', 'contents')
        self.put_object(bucket_name, 'foo', 'contents')
        self.put_object(bucket_name, 'bar.txt', 'contents')
        self.put_object(bucket_name, 'subdir/foo.txt', 'contents')
        p = aws('s3 ls s3://%s' % bucket_name)
        self.assertIn('PRE subdir/', p.stdout)
        self.assertIn('8 foo.txt', p.stdout)
        self.assertIn('8 foo', p.stdout)
        self.assertIn('8 bar.txt', p.stdout)

    def test_ls_recursive(self):
        bucket_name = self.create_bucket()
        self.put_object(bucket_name, 'foo.txt', 'contents')
        self.put_object(bucket_name, 'foo', 'contents')
        self.put_object(bucket_name, 'bar.txt', 'contents')
        self.put_object(bucket_name, 'subdir/foo.txt', 'contents')
        p = aws('s3 ls s3://%s --recursive' % bucket_name)
        self.assertIn('8 foo.txt', p.stdout)
        self.assertIn('8 foo', p.stdout)
        self.assertIn('8 bar.txt', p.stdout)
        self.assertIn('8 subdir/foo.txt', p.stdout)

    def test_ls_without_prefix(self):
        # The ls command does not require an s3:// prefix,
        # we're always listing s3 contents.
        bucket_name = self.create_bucket()
        self.put_object(bucket_name, 'foo.txt', 'contents')
        p = aws('s3 ls %s' % bucket_name)
        self.assertEqual(p.rc, 0)
        self.assertIn('foo.txt', p.stdout)


class TestMbRb(BaseS3CLICommand):
    """
    Tests primarily using ``rb`` and ``mb`` command.
    """
    def extra_setup(self):
        self.bucket_name = 'awscli-s3integ-' + str(random.randint(1, 1000))

    def test_mb_rb(self):
        p = aws('s3 mb s3://%s' % self.bucket_name)
        self.assert_no_errors(p)

        response = self.list_buckets()
        self.assertIn(self.bucket_name, [b['Name'] for b in response])

        p = aws('s3 rb s3://%s' % self.bucket_name)
        self.assert_no_errors(p)

    def test_fail_mb_rb(self):
        # Choose a bucket name that already exists.
        p = aws('s3 mb s3://mybucket')
        self.assertIn("BucketAlreadyExists", p.stdout)
        self.assertEqual(p.rc, 1)


class TestDryrun(BaseS3CLICommand):
    """
    This ensures that dryrun works.
    """
    def test_dryrun(self):
        # Make a bucket.
        bucket_name = self.create_bucket()
        foo_txt = self.files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s/ --dryrun' % (foo_txt, bucket_name))
        self.assertEqual(p.rc, 0)
        self.assert_no_errors(p)
        self.assertFalse(self.key_exists(bucket_name, 'foo.txt'))

    def test_dryrun_large_files(self):
        bucket_name = self.create_bucket()
        foo_txt = self.files.create_file('foo.txt', 'a' * 1024 * 1024 * 10)

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s/ --dryrun' % (foo_txt, bucket_name))
        self.assertEqual(p.rc, 0)
        self.assert_no_errors(p)
        self.assertFalse(
            self.key_exists(bucket_name, 'foo.txt'),
            "The key 'foo.txt' exists in S3. It looks like the --dryrun "
            "argument was not obeyed.")

    def test_dryrun_download_large_file(self):
        bucket_name = self.create_bucket()
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


@unittest.skipIf(platform.system() not in ['Darwin', 'Linux'],
                 'Memory tests only supported on mac/linux')
class TestMemoryUtilization(BaseS3CLICommand):
    # These tests verify the memory utilization and growth are what we expect.
    def extra_setup(self):
        expected_memory_usage = constants.NUM_THREADS * constants.CHUNKSIZE
        # margin for things like python VM overhead, botocore service
        # objects, etc.  1.5 is really generous, perhaps over time this can be
        # lowered.
        runtime_margin = 1.5
        self.max_mem_allowed = runtime_margin * expected_memory_usage

    def assert_max_memory_used(self, process, max_mem_allowed, full_command):
        peak_memory = max(process.memory_usage)
        if peak_memory > self.max_mem_allowed:
            failure_message = (
                'Exceeded max memory allowed (%s MB) for command '
                '"%s": %s MB' % (self.max_mem_allowed / 1024.0 / 1024.0,
                              full_command,
                              peak_memory / 1024.0 / 1024.0))
            self.fail(failure_message)

    def test_transfer_single_large_file(self):
        # 40MB will force a multipart upload.
        bucket_name = self.create_bucket()
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
        self.assert_max_memory_used(p, self.max_mem_allowed, download_full_command)


class TestWebsiteConfiguration(BaseS3CLICommand):
    def test_create_website_index_configuration(self):
        bucket_name = self.create_bucket()
        # Supply only --index-document argument.
        full_command = 's3 website %s --index-document index.html' % (bucket_name)
        p = aws(full_command)
        self.assertEqual(p.rc, 0)
        self.assert_no_errors(p)
        # Verify we have a bucket website configured.
        operation = self.service.get_operation('GetBucketWebsite')
        parsed = operation.call(
            self.endpoint, bucket=bucket_name)[1]
        self.assertEqual(parsed['IndexDocument']['Suffix'], 'index.html')
        self.assertEqual(parsed['ErrorDocument'], {})
        self.assertEqual(parsed['RoutingRules'], [])
        self.assertEqual(parsed['RedirectAllRequestsTo'], {})

    def test_create_website_index_and_error_configuration(self):
        bucket_name = self.create_bucket()
        # Supply both --index-document and --error-document arguments.
        p = aws('s3 website %s --index-document index.html '
                '--error-document error.html' % bucket_name)
        self.assertEqual(p.rc, 0)
        self.assert_no_errors(p)
        # Verify we have a bucket website configured.
        operation = self.service.get_operation('GetBucketWebsite')
        parsed = operation.call(
            self.endpoint, bucket=bucket_name)[1]
        self.assertEqual(parsed['IndexDocument']['Suffix'], 'index.html')
        self.assertEqual(parsed['ErrorDocument']['Key'], 'error.html')
        self.assertEqual(parsed['RoutingRules'], [])
        self.assertEqual(parsed['RedirectAllRequestsTo'], {})


class TestIncludeExcludeFilters(BaseS3CLICommand):
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
        p = aws('s3 cp %s s3://random-bucket-name/ --dryrun --exclude foo.txt'
                 % full_path)
        self.assert_no_files_would_be_uploaded(p)

    def test_cwd_doesnt_matter(self):
        full_path = self.files.create_file('foo.txt', 'this is foo.txt')
        with cd(os.path.expanduser('~')):
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
        self.assertRegexpMatches(p.stdout,
                                 r'\(dryrun\) upload:.*test/foo.txt.*')

    def test_s3_filtering(self):
        # Should behave the same as local file filtering.
        bucket_name = self.create_bucket()
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
        self.assertRegexpMatches(p.stdout, r'\(dryrun\) delete:.*baz.jpg.*')
        self.assertNotIn(p.stdout, 'bar.txt')
        self.assertNotIn(p.stdout, 'foo.txt')

    def test_exclude_filter_with_delete(self):
        # Test for: https://github.com/aws/aws-cli/issues/778
        bucket_name = self.create_bucket()
        first = self.files.create_file('foo.txt', 'contents')
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
             "end, the 'bar.py' file was deleted even though it was excluded."))


class TestFileWithSpaces(BaseS3CLICommand):
    def test_upload_download_file_with_spaces(self):
        bucket_name = self.create_bucket()
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
        bucket_name = self.create_bucket()
        bucket_name = self.create_bucket()
        filename = self.files.create_file('with space.txt', 'contents')
        p = aws('s3 sync %s s3://%s/' % (self.files.rootdir,
                                         bucket_name))
        self.assert_no_errors(p)
        # Now syncing again should *not* trigger any uploads (i.e we should
        # get nothing on stdout).
        p2 = aws('s3 sync %s s3://%s/' % (self.files.rootdir,
                                          bucket_name))
        self.assertEqual(p2.stdout, '')
        self.assertEqual(p2.stderr, '')
        self.assertEqual(p2.rc, 0)


if __name__ == "__main__":
    unittest.main()
