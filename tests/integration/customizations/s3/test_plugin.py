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

from tests.integration import Result, aws


class TestLs(unittest.TestCase):
    """
    This tests using the ``ls`` command.
    """
    def test_ls_bucket(self):
        """
        Test the ability to list buckets.
        """
        p = aws('s3 ls')
        self.assertEqual(p.rc, 0)
        self.assertNotIn("Error:", p.stdout)
        self.assertNotIn("failed:", p.stdout)

    def test_fail_format(self):
        """
        Test to ensure parameter checking works.
        """
        cmds = ['s3 cp', 's3 ls test', 's3 ls s3:// --dryrun']
        for cmd in cmds:
            p = aws(cmd)
            self.assertNotEqual(p.rc, 0)


class TestMbRb(unittest.TestCase):
    """
    Tests primarily using ``rb`` and ``mb`` command.
    """
    def setUp(self):
        rand1 = random.randrange(5000)
        rand2 = random.randrange(5000)
        self.bucket_name = str(rand1) + 'mybucket' + str(rand2)

    def test_mb_rb(self):
        """
        Tests the ability to make and remove buckets.
        """
        p = aws('s3 mb s3://%s' % self.bucket_name)
        self.assertEqual(p.rc, 0)
        self.assertNotIn("Error:", p.stdout)
        self.assertNotIn("failed:", p.stdout)

        p = aws('s3 ls')
        self.assertIn(self.bucket_name, p.stdout)

        p = aws('s3 rb s3://%s' % self.bucket_name)
        self.assertEqual(p.rc, 0)
        self.assertNotIn("Error:", p.stdout)
        self.assertNotIn("failed:", p.stdout)

        p = aws('s3 ls')
        self.assertNotIn(self.bucket_name, p.stdout)

    def test_fail_mb_rb(self):
        """
        Makes sure that mb and rb fail properly.
        Note: mybucket is not available to create and therefore
        you cannot delete it as well.
        """
        bucket_name = "mybucket"
        p = aws('s3 mb s3://%s' % bucket_name)
        self.assertIn("Error:", p.stdout)
        self.assertIn("failed:", p.stdout)

        bucket_name = "mybucket"
        p = aws('s3 rb s3://%s' % bucket_name)
        self.assertIn("Error:", p.stdout)
        self.assertIn("failed:", p.stdout)


class TestDryrun(unittest.TestCase):
    """
    This ensures that dryrun works.
    """
    def setUp(self):
        self.filename1 = 'testTest1.txt'
        path = os.path.abspath('.') + os.sep + self.filename1
        with open(path, 'wb') as file1:
            string1 = b"This is a test."
            file1.write(string1)

        rand1 = random.randrange(5000)
        rand2 = random.randrange(5000)
        self.bucket_name = str(rand1) + 'mybucket' + str(rand2) + '/'

    def tearDown(self):
        p = aws('s3 rb s3://%s' % self.bucket_name)
        if os.path.exists(self.filename1):
            os.remove(self.filename1)

    def test_dryrun(self):
        # Make a bucket.
        p = aws('s3 mb s3://%s' % self.bucket_name)

        # Copy file into bucket.
        p = aws('s3 cp %s s3://%s --dryrun' % (self.filename1,
                                               self.bucket_name))
        self.assertEqual(p.rc, 0)
        self.assertNotIn("Error:", p.stdout)
        self.assertNotIn("failed:", p.stdout)

        # Make sure the file is not in the bucket.
        p = aws('s3 ls s3://%s' % self.bucket_name)
        self.assertNotIn(self.filename1, p.stdout)


class TestCpMv(unittest.TestCase):
    def setUp(self):
        self.filename1 = 'testTest1.txt'
        self.filename2 = 'testTest2.txt'
        path = os.path.abspath('.') + os.sep + self.filename1
        with open(path, 'wb') as file1:
            string1 = b"This is a test."
            file1.write(string1)

        rand1 = random.randrange(5000)
        rand2 = random.randrange(5000)
        self.bucket_name = str(rand1) + 'mybucket' + str(rand2) + '/'

        rand1 = random.randrange(5000)
        rand2 = random.randrange(5000)
        self.bucket_name2 = str(rand1) + 'mybucket' + str(rand2) + '/'

    def tearDown(self):
        if os.path.exists(self.filename1):
            os.remove(self.filename1)
        aws('s3 rb --force s3://%s' % self.bucket_name)
        aws('s3 rb --force s3://%s' % self.bucket_name2)
        if os.path.exists(self.filename2):
            os.remove(self.filename2)

    def test_cp_mv_cp(self):
        """
        This tests the ability to put a single file in s3
        move it to a different bucket.
        and download the file locally
        """
        # Make a bucket.
        p = aws('s3 mb s3://%s' % self.bucket_name)

        # copy file into bucket.
        p = aws('s3 cp %s s3://%s' % (self.filename1, self.bucket_name))
        self.assertEqual(p.rc, 0)
        self.assertNotIn("Error:", p.stdout)
        self.assertNotIn("failed:", p.stdout)

        # Make sure object is in bucket.
        p = aws('s3 ls s3://%s' % self.bucket_name)
        self.assertIn(self.filename1, p.stdout)

        # Make another bucket.
        p = aws('s3 mb s3://%s' % self.bucket_name2)

        # Move the file from the original bucket to the new bucket.
        p = aws('s3 mv s3://%s s3://%s' % (self.bucket_name + self.filename1,
                                           self.bucket_name2))

        # Ensure it is no longer in the original bucket.
        p = aws('s3 ls s3://%s' % self.bucket_name)
        self.assertNotIn(self.filename1, p.stdout)

        # Ensure it is in the new bucket.
        p = aws('s3 ls s3://%s' % self.bucket_name2)
        self.assertIn(self.filename1, p.stdout)

        # Make a new name for the file and copy it locally.
        p = aws('s3 cp s3://%s %s' % (self.bucket_name2 + self.filename1,
                                      self.filename2))

        with open(self.filename2, 'rb') as file2:
            data = file2.read()

        # Ensure the contents are the same.
        self.assertEqual(data, b'This is a test.')


class TestSync(unittest.TestCase):
    def setUp(self):
        filename1 = 'testTest1.txt'
        filename2 = 'testTest2.txt'
        self.path1 = os.path.abspath('.') + os.sep + 'some_dir' \
            + os.sep + filename1
        self.path2 = os.path.abspath('.') + os.sep + 'some_dir' \
            + os.sep + filename2
        if not os.path.exists('some_dir'):
            os.mkdir('some_dir')
        with open(self.path1, 'wb') as file1:
            string1 = b"This is a test."
            file1.write(string1)
        with open(self.path2, 'wb') as file2:
            string2 = b"Another Test."
            file2.write(string2)

    def tearDown(self):
        if os.path.exists(self.path1):
            os.remove(self.path1)
        if os.path.exists(self.path2):
            os.remove(self.path2)
        if os.path.exists('some_dir'):
            os.rmdir('some_dir')

    def test_sync(self):
        """
        Test the ability to preform a ``sync``.
        """
        filename1 = 'testTest1.txt'
        filename2 = 'testTest2.txt'

        # Make a bucket.
        rand1 = random.randrange(5000)
        rand2 = random.randrange(5000)
        bucket_name = str(rand1) + 'mybucket' + str(rand2) + '/'
        p = aws('s3 mb s3://%s' % bucket_name)

        # Sync the directory and the bucket.
        p = aws('s3 sync %s s3://%s' % ('some_dir', bucket_name))
        self.assertEqual(p.rc, 0)
        self.assertNotIn("Error:", p.stdout)
        self.assertNotIn("failed:", p.stdout)

        # Ensure both files are in the bucket.
        p = aws('s3 ls s3://%s' % bucket_name)
        self.assertIn(filename1, p.stdout)
        self.assertIn(filename2, p.stdout)

        # Test force remove bucket which is a recursive delete.
        p = aws('s3 rb --force s3://%s' % bucket_name)
        self.assertEqual(p.rc, 0)
        self.assertNotIn("Error:", p.stdout)
        self.assertNotIn("failed:", p.stdout)

        # Make sure the recursive delete was successful.
        p = aws('s3 ls s3://%s' % bucket_name)
        self.assertNotIn(filename1, p.stdout)
        self.assertNotIn(filename2, p.stdout)

        # Ensure the bucket was deleted as well.
        p = aws('s3 ls')
        self.assertNotIn(bucket_name, p.stdout)


class UnicodeTest(unittest.TestCase):
    """
    The purpose of these tests are to ensure that the commands can handle
    unicode characters in both keyname and from those generated for both
    uploading and downloading files.
    """
    def setUp(self):
        self.filename1 = 'êxample.txt'
        self.filename2 = 'êxample2.txt'
        self.path1 = os.path.abspath('.') + os.sep + 'some_dir' \
            + os.sep+self.filename1
        self.path2 = os.path.abspath('.') + os.sep + 'some_dir' \
            + os.sep+self.filename2
        if not os.path.exists('some_dir'):
            os.mkdir('some_dir')
        with open(self.path1, 'wb') as file1:
            string1 = b"This is a test."
            file1.write(string1)
        rand1 = random.randrange(5000)
        rand2 = random.randrange(5000)
        self.bucket_name = str(rand1) + 'mybucket' + str(rand2) + '/'
        p = aws('s3 mb s3://%s' % self.bucket_name)

    def tearDown(self):
        aws('s3 rm --recursive s3://%s --quiet' % self.bucket_name)
        aws('s3 rb s3://%s' % self.bucket_name)
        if os.path.exists(self.path1):
            os.remove(self.path1)
        if os.path.exists(self.path2):
            os.remove(self.path2)
        if os.path.exists('some_dir'):
            os.rmdir('some_dir')

    def test_cp(self):
        file_path1 = 'some_dir' + os.sep + self.filename1
        file_path2 = 'some_dir' + os.sep + self.filename2
        p = aws('s3 cp %s s3://%s --quiet' % (file_path1, self.bucket_name))
        self.assertEqual(p.rc, 0)
        s3_path = self.bucket_name + self.filename1
        p = aws('s3 cp s3://%s %s --quiet' % (s3_path, file_path2))
        self.assertEqual(p.rc, 0)
        with open(self.path2, 'rb') as file2:
            data = file2.read()

        # Ensure the contents are the same.
        self.assertEqual(data, b'This is a test.')

    def test_recur_cp(self):
        p = aws('s3 cp %s s3://%s --quiet --recursive' % ('some_dir',
                                                          self.bucket_name))
        self.assertEqual(p.rc, 0)
        p = aws('s3 cp s3://%s %s --quiet --recursive' % (self.bucket_name,
                                                          'some_dir'))
        self.assertEqual(p.rc, 0)
        with open(self.path1, 'rb') as file2:
            data = file2.read()

        # Ensure the contents are the same.
        self.assertEqual(data, b'This is a test.')


if __name__ == "__main__":
    unittest.main()
