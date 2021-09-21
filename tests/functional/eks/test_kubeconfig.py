# Copyright 2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import tempfile
import mock

from botocore.compat import OrderedDict

from awscli.testutils import unittest
from tests.functional.eks.test_util import get_testdata
from awscli.customizations.eks.kubeconfig import (_get_new_kubeconfig_content,
                                                  KubeconfigWriter,
                                                  KubeconfigLoader,
                                                  KubeconfigValidator,
                                                  Kubeconfig,
                                                  KubeconfigInaccessableError)
class TestKubeconfigWriter(unittest.TestCase):
    def setUp(self):
        self._writer = KubeconfigWriter()

    def test_write_order(self):
        content = OrderedDict([
            ("current-context", "context"),
            ("apiVersion", "v1")
        ])
        file_to_write = tempfile.NamedTemporaryFile(mode='w').name
        self.addCleanup(os.remove, file_to_write)

        config = Kubeconfig(file_to_write, content)
        self._writer.write_kubeconfig(config)

        with open(file_to_write, 'r') as stream:
            self.assertMultiLineEqual(stream.read(),
                                      "current-context: context\n"
                                      "apiVersion: v1\n")
    def test_write_makedirs(self):
        content = OrderedDict([
            ("current-context", "context"),
            ("apiVersion", "v1")
        ])
        containing_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, containing_dir)
        config_path = os.path.join(containing_dir,
                                   "dir1",
                                   "dir2",
                                   "dir3")

        config = Kubeconfig(config_path, content)
        self._writer.write_kubeconfig(config)

        with open(config_path, 'r') as stream:
            self.assertMultiLineEqual(stream.read(),
                                      "current-context: context\n"
                                      "apiVersion: v1\n")

    def test_write_directory(self):
        content = OrderedDict([
            ("current-context", "context"),
            ("apiVersion", "v1")
        ])
        containing_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, containing_dir)

        config = Kubeconfig(containing_dir, content)
        self.assertRaises(KubeconfigInaccessableError,
                          self._writer.write_kubeconfig,
                          config)

class TestKubeconfigLoader(unittest.TestCase):
    def setUp(self):
        # This mock validator allows all kubeconfigs
        self._validator = mock.Mock(spec=KubeconfigValidator)
        self._loader = KubeconfigLoader(self._validator)

        self._temp_directory = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self._temp_directory)

    def _clone_config(self, config):
        """
        Copies the testdata named config into the temp directory,
        Returns the new path

        :param config: The name of the testdata to copy
        :type config: str
        """
        old_path = os.path.abspath(get_testdata(config))
        new_path = os.path.join(self._temp_directory, config)
        shutil.copy2(old_path, 
                     new_path)
        return new_path

    def test_load_simple(self):
        simple_path = self._clone_config("valid_simple")
        content = OrderedDict([
            ("apiVersion", "v1"),
            ("clusters", [
                OrderedDict([
                    ("cluster", OrderedDict([
                        ("server", "simple")
                    ])),
                    ("name", "simple")
                ])
            ]),
            ("contexts", None),
            ("current-context", "simple"),
            ("kind", "Config"),
            ("preferences", OrderedDict()),
            ("users", None)
        ])
        loaded_config = self._loader.load_kubeconfig(simple_path)
        self.assertEqual(loaded_config.content, content)
        self._validator.validate_config.called_with(Kubeconfig(simple_path, 
                                                               content))

    def test_load_noexist(self):
        no_exist_path = os.path.join(self._temp_directory,
                                     "this_does_not_exist")
        loaded_config = self._loader.load_kubeconfig(no_exist_path)
        self.assertEqual(loaded_config.content, 
                         _get_new_kubeconfig_content())
        self._validator.validate_config.called_with(
            Kubeconfig(no_exist_path, _get_new_kubeconfig_content()))

    def test_load_empty(self):
        empty_path = self._clone_config("valid_empty_existing")
        loaded_config = self._loader.load_kubeconfig(empty_path)
        self.assertEqual(loaded_config.content, 
                         _get_new_kubeconfig_content())
        self._validator.validate_config.called_with(
            Kubeconfig(empty_path, 
                       _get_new_kubeconfig_content()))

    def test_load_directory(self):
        current_directory = self._temp_directory
        self.assertRaises(KubeconfigInaccessableError,
                          self._loader.load_kubeconfig,
                          current_directory)
        self._validator.validate_config.assert_not_called()