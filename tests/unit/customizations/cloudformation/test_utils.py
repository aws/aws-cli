# Copyright 2014 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0e
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

import os
import random
import shutil
import string
import tempfile
import unittest

from awscli.customizations.cloudformation import utils


def random_string(n=10):
    return ''.join(random.choice(string.ascii_letters) for _ in range(n))


def new_temp_file(tempdir):
    filepath = os.path.join(tempdir, random_string())
    with open(filepath, "wb") as f:
        f.write(random_string(100))
    return filepath


def with_temp_dir(f):
    def test_wrapper(self, *args, **kwargs):
        tempdir = tempfile.mkdtemp()
        f(self, tempdir, *args, **kwargs)
        shutil.rmtree(tempdir)
    return test_wrapper


class TestUtils(unittest.TestCase):
    @with_temp_dir
    def test_hash_file(self, tempdir):
        filepath = new_temp_file(tempdir)
        first_hash = utils.hash_file(filepath)
        second_hash = utils.hash_file(filepath)
        self.assertEquals(first_hash, second_hash)

    @with_temp_dir
    def test_hash_file_returns_different(self, tempdir):
        filepath1 = new_temp_file(tempdir)
        filepath2 = new_temp_file(tempdir)
        first_hash = utils.hash_file(filepath1)
        second_hash = utils.hash_file(filepath2)
        self.assertNotEquals(first_hash, second_hash)

    @with_temp_dir
    def test_hash_dir(self, tempdir):
        for _ in range(random.randint(1, 10)):
            new_temp_file(tempdir)
        first_hash = utils.hash_dir(tempdir)
        second_hash = utils.hash_dir(tempdir)
        self.assertEquals(first_hash, second_hash)

    @with_temp_dir
    @with_temp_dir
    def test_hash_dir_different(self, tempdir1, tempdir2):
        for _ in range(random.randint(1, 10)):
            new_temp_file(tempdir1)
        for _ in range(random.randint(1, 10)):
            new_temp_file(tempdir2)
        first_hash = utils.hash_dir(tempdir1)
        second_hash = utils.hash_dir(tempdir2)
        self.assertNotEquals(first_hash, second_hash)

    @with_temp_dir
    def test_hash_dir_with_nested_dir(self, tempdir):
        for _ in range(random.randint(1, 10)):
            new_temp_file(tempdir)
        first_hash = utils.hash_dir(tempdir)
        nested_dir = os.path.join(tempdir, random_string())
        os.mkdir(nested_dir)
        for _ in range(random.randint(1, 10)):
            new_temp_file(nested_dir)
        second_hash = utils.hash_dir(tempdir)
        self.assertNotEqual(first_hash, second_hash)

    @with_temp_dir
    def test_hash_dir_not_dir(self, tempdir):
        filepath = new_temp_file(tempdir)
        self.assertRaises(AttributeError, lambda: utils.hash_dir(filepath))
