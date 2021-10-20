# Copyright 2015 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
# http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
import os
import shutil

from botocore import loaders
from tests import unittest, temporary_file


class TestLoaderAllowsDataPathOverride(unittest.TestCase):
    def create_file(self, f, contents, name):
        f.write(contents)
        f.flush()
        dirname = os.path.dirname(os.path.abspath(f.name))
        override_name = os.path.join(dirname, name)
        shutil.copy(f.name, override_name)
        return override_name

    def test_can_override_session(self):
        with temporary_file('w') as f:
            # We're going to override _retry.json in 
            # botocore/data by setting our own data directory.
            override_name = self.create_file(
                f, contents='{"foo": "bar"}', name='_retry.json')
            new_data_path = os.path.dirname(override_name)
            loader = loaders.create_loader(search_path_string=new_data_path)

            new_content = loader.load_data('_retry')
            # This should contain the content we just created.
            self.assertEqual(new_content, {"foo": "bar"})
