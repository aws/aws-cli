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

import botocore.session

from tests.integration import aws
from tests.unit.customizations.s3 import create_bucket as _create_bucket


class FileCreator(object):
    def __init__(self):
        self.rootdir = tempfile.mkdtemp()

    def remove_all(self):
        shutil.rmtree(self.rootdir)

    def create_file(self, filename, contents):
        """Creates a file in a tmpdir

        ``filename`` should be a relative path, e.g. "foo/bar/baz.txt"
        It will be translated into a full path in a tmp dir.

        Returns the full path to the file.
        """
        full_path = os.path.join(self.rootdir, filename)
        with open(full_path, 'w') as f:
            f.write(contents)
        return full_path

    def full_path(self, filename):
        """Translate relative path to full path in temp dir.

        f.full_path('foo/bar.txt') -> /tmp/asdfasd/foo/bar.txt
        """
        return os.path.join(self.rootdir, filename)


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

    def put_object(self, bucket_name, key_name, contents):
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
        self.assertEqual(p.rc, 0)
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
        aws('s3 mv s3://%s/foo.txt %s' % (bucket_name, full_path))
        self.assertTrue(os.path.exists(full_path))
        with open(full_path, 'r') as f:
            self.assertEqual(f.read(), 'this is foo.txt')

    def test_mv_s3_to_s3(self):
        from_bucket = self.create_bucket()
        to_bucket = self.create_bucket()
        self.put_object(from_bucket, 'foo.txt', 'this is foo.txt')

        aws('s3 mv s3://%s/foo.txt s3://%s/foo.txt' % (from_bucket, to_bucket))
        contents = self.get_key_contents(to_bucket, 'foo.txt')
        self.assertEqual(contents, 'this is foo.txt')
        # And verify that the object no longer exists in the from_bucket.
        self.assertTrue(not self.key_exists(from_bucket, key_name='foo.txt'))

    def test_mv_with_large_file(self):
        bucket_name = self.create_bucket()
        # 40MB will force a multipart upload.
        file_contents = 'abcd' * (1024 * 1024 * 10)
        foo_txt = self.files.create_file('foo.txt', file_contents)
        aws('s3 mv %s s3://%s/foo.txt' % (foo_txt, bucket_name))
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

        with open(full_path, 'r') as f:
            self.assertEqual(f.read(), 'this is foo.txt')

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
        # TODO: assert error code test.
        self.assertIn("BucketAlreadyExists", p.stdout)


class TestDryrun(BaseS3CLICommand):
    """
    This ensures that dryrun works.
    """
    def test_dryrun(self):
        # Make a bucket.
        bucket_name = self.create_bucket()
        foo_txt = self.files.create_file('foo.txt', 'foo contents')

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s --dryrun' % (foo_txt, bucket_name))
        self.assertEqual(p.rc, 0)
        self.assert_no_errors(p)
        self.assertFalse(self.key_exists(bucket_name, 'foo.txt'))


if __name__ == "__main__":
    unittest.main()
