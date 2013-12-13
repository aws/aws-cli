
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
import random
from tests import unittest
import tempfile
import shutil
import platform
import contextlib

import botocore.session

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
        aws('s3 mv %s s3://%s/foo.txt' % (full_path,
                                          bucket_name))
        # When we move an object, the local file is gone:
        self.assertTrue(not os.path.exists(full_path))
        # And now resides in s3.
        contents = self.get_key_contents(bucket_name, 'foo.txt')
        self.assertEqual(contents, 'this is foo.txt')

    def test_mv_s3_to_local(self):
        bucket_name = self.create_bucket()
        self.put_object(bucket_name, 'foo.txt', 'this is foo.txt')
        full_path = self.files.full_path('foo.txt')
        self.assertTrue(self.key_exists(bucket_name, key_name='foo.txt'))
        aws('s3 mv s3://%s/foo.txt %s' % (bucket_name, full_path))
        self.assertTrue(os.path.exists(full_path))
        with open(full_path, 'r') as f:
            self.assertEqual(f.read(), 'this is foo.txt')
        # The s3 file should not be there anymore.
        self.assertTrue(not self.key_exists(bucket_name, key_name='foo.txt'))

    def test_mv_s3_to_s3(self):
        from_bucket = self.create_bucket()
        to_bucket = self.create_bucket()
        self.put_object(from_bucket, 'foo.txt', 'this is foo.txt')

        aws('s3 mv s3://%s/foo.txt s3://%s/foo.txt' % (from_bucket, to_bucket))
        contents = self.get_key_contents(to_bucket, 'foo.txt')
        self.assertEqual(contents, 'this is foo.txt')
        # And verify that the object no longer exists in the from_bucket.
        self.assertTrue(not self.key_exists(from_bucket, key_name='foo.txt'))

    def test_mv_s3_to_s3_multipart(self):
        from_bucket = self.create_bucket()
        to_bucket = self.create_bucket()
        file_contents = 'abcd' * (1024 * 1024 * 10)
        self.put_object(from_bucket, 'foo.txt', file_contents)

        aws('s3 mv s3://%s/foo.txt s3://%s/foo.txt' % (from_bucket, to_bucket))
        contents = self.get_key_contents(to_bucket, 'foo.txt')
        self.assertEqual(contents, file_contents)
        # And verify that the object no longer exists in the from_bucket.
        self.assertTrue(not self.key_exists(from_bucket, key_name='foo.txt'))

    def test_mv_s3_to_s3_multipart_recursive(self):
        from_bucket = self.create_bucket()
        to_bucket = self.create_bucket()

        large_file_contents = 'abcd' * (1024 * 1024 * 10)
        small_file_contents = 'small file contents'
        self.put_object(from_bucket, 'largefile', large_file_contents)
        self.put_object(from_bucket, 'smallfile', small_file_contents)

        aws('s3 mv s3://%s/ s3://%s/ --recursive' % (from_bucket, to_bucket))
        # Nothing's in the from_bucket.
        self.assertTrue(not self.key_exists(from_bucket, key_name='largefile'))
        self.assertTrue(not self.key_exists(from_bucket, key_name='smallfile'))

        # And both files are in the to_bucket.
        self.assertTrue(self.key_exists(to_bucket, key_name='largefile'))
        self.assertTrue(self.key_exists(to_bucket, key_name='smallfile'))

        # And the contents are what we expect.
        self.assertEqual(self.get_key_contents(to_bucket, 'smallfile'),
                         small_file_contents)
        self.assertEqual(self.get_key_contents(to_bucket, 'largefile'),
                         large_file_contents)

    def test_mv_with_large_file(self):
        bucket_name = self.create_bucket()
        # 40MB will force a multipart upload.
        file_contents = 'abcd' * (1024 * 1024 * 10)
        foo_txt = self.files.create_file('foo.txt', file_contents)
        p = aws('s3 mv %s s3://%s/foo.txt' % (foo_txt, bucket_name))
        self.assert_no_errors(p)
        # When we move an object, the local file is gone:
        self.assertTrue(not os.path.exists(foo_txt))
        # And now resides in s3.
        contents = self.get_key_contents(bucket_name, 'foo.txt')
        self.assertEqual(len(contents), len(file_contents))

        # Now verify we can download this file.
        p = aws('s3 mv s3://%s/foo.txt %s' % (bucket_name, foo_txt))
        self.assert_no_errors(p)
        self.assertTrue(os.path.exists(foo_txt))
        self.assertEqual(os.path.getsize(foo_txt), len(file_contents))

    def test_mv_to_nonexistent_bucket(self):
        full_path = self.files.create_file('foo.txt', 'this is foo.txt')
        p = aws('s3 mv %s s3://bad-noexist-13143242/foo.txt' % (full_path,))
        self.assertEqual(p.rc, 1)


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

    def test_cp_s3_s3_multipart(self):
        from_bucket = self.create_bucket()
        to_bucket = self.create_bucket()
        file_contents = 'abcd' * (1024 * 1024 * 10)
        self.put_object(from_bucket, 'foo.txt', file_contents)

        aws('s3 cp s3://%s/foo.txt s3://%s/foo.txt' % (from_bucket, to_bucket))
        contents = self.get_key_contents(to_bucket, 'foo.txt')
        self.assertEqual(contents, file_contents)
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
        foo_contents = 'abcd' * (1024 * 1024 * 10)
        self.put_object(bucket_name, key_name='foo.txt', contents=foo_contents)
        local_foo_txt = self.files.full_path('foo.txt')
        p = aws('s3 cp s3://%s/foo.txt %s' % (bucket_name, local_foo_txt))
        self.assert_no_errors(p)
        self.assertEqual(os.path.getsize(local_foo_txt), len(foo_contents))

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
        foo_txt = self.files.create_file('foo.txt', 'foo contents')
        bar_txt = self.files.create_file('bar.txt', 'bar contents')

        # Sync the directory and the bucket.
        p = aws('s3 sync %s s3://noexist-bkt-nme-1412' % (self.files.rootdir,))
        self.assertEqual(p.rc, 1)

    def test_sync_with_empty_files(self):
        foo_txt = self.files.create_file('foo.txt', 'foo contents')
        empty_txt = self.files.create_file('bar.txt', contents='')
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
        p = aws('s3 sync %s s3://%s/' % (self.files.rootdir, bucket_name))

        # Now here's the issue.  If we try to sync the contents down
        # with the --delete flag we should *not* see any output, the
        # sync operation should determine that nothing is different and
        # therefore do nothing.  We can just use --dryrun to show the issue.
        p = aws('s3 sync s3://%s/ %s --dryrun' % (
            bucket_name, self.files.rootdir))
        # These assertion methods will give better error messages than just
        # checking if the output is empty.
        self.assertNotIn('download:', p.stdout)
        self.assertNotIn('delete:', p.stdout)
        self.assertEqual('', p.stdout)


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
        local_example1_txt = self.files.create_file('êxample.txt', 'example1 contents')
        s3_example1_txt = 's3://%s/%s' % (bucket_name,
                                          os.path.basename(local_example1_txt))
        local_example2_txt = self.files.full_path('êxample2.txt')

        p = aws('s3 cp %s %s' % (local_example1_txt, s3_example1_txt))
        self.assert_no_errors(p)

        # Download the file to the second example2.txt filename.
        p = aws('s3 cp %s %s --quiet' % (s3_example1_txt, local_example2_txt))
        self.assert_no_errors(p)
        with open(local_example2_txt, 'rb') as f:
            self.assertEqual(f.read(), b'example1 contents')

    def test_recursive_cp(self):
        bucket_name = self.create_bucket()
        local_example1_txt = self.files.create_file('êxample1.txt', 'example1 contents')
        local_example2_txt = self.files.create_file('êxample2.txt', 'example2 contents')
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
    def test_create_website_configuration(self):
        bucket_name = self.create_bucket()
        full_command = 's3 website %s --index-document index.html' % (bucket_name)
        p = aws(full_command)
        self.assertEqual(p.rc, 0)
        self.assert_no_errors(p)
        # Verify we have a bucket website configured.
        operation = self.service.get_operation('GetBucketWebsite')
        parsed = operation.call(
            self.endpoint, bucket=bucket_name)[1]
        self.assertEqual(parsed['IndexDocument']['Suffix'], 'index.html')


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

        p2 = aws('s3 cp %s s3://random-bucket-name/ --dryrun --exclude "*"'
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
            p = aws('s3 cp %s s3://random-bucket-name/ --dryrun --exclude "*"'
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
        p = aws('s3 cp %s s3://random-bucket-name/ --dryrun --exclude "*" '
                 '--recursive' % self.files.rootdir)
        self.assert_no_files_would_be_uploaded(p)

        # We can include the test directory though.
        p = aws('s3 cp %s s3://random-bucket-name/ --dryrun '
                '--exclude "*" --include "test/*" --recursive'
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
        p = aws('s3 rm s3://%s/ --dryrun --exclude "*" --recursive'
                % bucket_name)
        self.assert_no_files_would_be_uploaded(p)

        p = aws(
            's3 rm s3://%s/ --dryrun --exclude "*.jpg" --exclude "*.txt" '
            '--recursive' % bucket_name)
        self.assert_no_files_would_be_uploaded(p)

        p = aws('s3 rm s3://%s/ --dryrun --exclude "*.txt" --recursive'
                % bucket_name)
        self.assert_no_errors(p)
        self.assertRegexpMatches(p.stdout, r'\(dryrun\) delete:.*baz.jpg.*')
        self.assertNotIn(p.stdout, 'bar.txt')
        self.assertNotIn(p.stdout, 'foo.txt')


if __name__ == "__main__":
    unittest.main()
