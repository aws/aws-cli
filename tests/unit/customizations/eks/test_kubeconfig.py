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

import glob
import os
import mock
import tempfile
import shutil
from botocore.compat import OrderedDict

from awscli.testutils import unittest
from awscli.customizations.utils import uni_print
from awscli.customizations.eks.kubeconfig import (KubeconfigError,
                                                  KubeconfigInaccessableError,
                                                  KubeconfigCorruptedError,
                                                  Kubeconfig,
                                                  KubeconfigValidator,
                                                  KubeconfigLoader,
                                                  KubeconfigAppender,
                                                  KubeconfigWriter,
                                                  _get_new_kubeconfig_content,
                                                  )
from awscli.customizations.eks.exceptions import EKSError
from awscli.customizations.eks.ordered_yaml import ordered_yaml_load
from tests.functional.eks.test_util import get_testdata

class TestKubeconfig(unittest.TestCase):
    def setUp(self):
        self._content = OrderedDict([
            ("apiVersion", "v1")
        ])
        self._path = "/some_path"

    def test_no_content(self):
        config = Kubeconfig(self._path, None)
        self.assertEqual(config.content, 
                         _get_new_kubeconfig_content())

    def test_has_cluster(self):
        self._content["clusters"] = [
            OrderedDict([
                ("cluster", None),
                ("name", "clustername")
            ]),
            OrderedDict([
                ("cluster", None),
                ("name", "anotherclustername")
            ])
        ]

        config = Kubeconfig(self._path, self._content)
        self.assertTrue(config.has_cluster("clustername"))
        self.assertFalse(config.has_cluster("othercluster"))

    def test_has_cluster_with_no_clusters(self):
        config = Kubeconfig(self._path, self._content)
        self.assertFalse(config.has_cluster("clustername"))

class TestKubeconfigValidator(unittest.TestCase):
    def setUp(self):
        self._validator = KubeconfigValidator()

    def test_valid(self):
        valid_cases = glob.glob(get_testdata( "valid_*" ))
        for case in valid_cases:
            with open(case, 'r') as stream:
                content_dict = ordered_yaml_load(stream)
            if content_dict is not None:
                config = Kubeconfig(None, content_dict)
                try:
                    self._validator.validate_config(config)
                except KubeconfigError as e:
                    self.fail("Valid file {0} raised {1}.".format(case, e))

    def test_invalid(self):
        invalid_cases = glob.glob(get_testdata("invalid_*"))
        for case in invalid_cases:
            with open(case, 'r') as stream:
                content_dict = ordered_yaml_load(stream)
            config = Kubeconfig(None, content_dict)
            self.assertRaises(KubeconfigCorruptedError,
                              self._validator.validate_config, 
                              config)

class TestKubeconfigAppender(unittest.TestCase):
    def setUp(self):
        self._appender = KubeconfigAppender()

    def test_basic_insert(self):
        initial = OrderedDict([
            ("apiVersion", "v1"),
            ("clusters", [
                OrderedDict([
                    ("cluster", OrderedDict([
                        ("certificate-authority-data", "data1"),
                        ("server", "endpoint1")
                    ])),
                ("name", "oldclustername")
                ])
            ]),
            ("contexts", []),
            ("current-context", "simple"),
            ("kind", "Config"),
            ("preferences", OrderedDict()),
            ("users", [])
        ])
        cluster = OrderedDict([
            ("cluster", OrderedDict([
                ("certificate-authority-data", "data2"),
                ("server", "endpoint2")
            ])),
            ("name", "clustername")
        ])
        cluster_added_correct = OrderedDict([
            ("apiVersion", "v1"),
            ("clusters", [
                OrderedDict([
                    ("cluster", OrderedDict([
                        ("certificate-authority-data", "data1"),
                        ("server", "endpoint1")
                    ])),
                ("name", "oldclustername")
            ]),
                OrderedDict([
                    ("cluster", OrderedDict([
                        ("certificate-authority-data", "data2"),
                        ("server", "endpoint2")
                    ])),
                ("name", "clustername")
                ])
            ]),
            ("contexts", []),
            ("current-context", "simple"),
            ("kind", "Config"),
            ("preferences", OrderedDict()),
            ("users", [])
        ])
        cluster_added = self._appender.insert_entry(Kubeconfig(None, initial),
                                                    "clusters",
                                                    cluster)
        self.assertDictEqual(cluster_added.content, cluster_added_correct)

    def test_update_existing(self):
        initial = OrderedDict([
            ("apiVersion", "v1"),
            ("clusters", [
                OrderedDict([
                    ("cluster", OrderedDict([
                        ("server", "endpoint")
                    ])),
                    ("name", "clustername")
                ])
            ]),
            ("contexts", []),
            ("current-context", None),
            ("kind", "Config"),
            ("preferences", OrderedDict()),
            ("users", [])
        ])
        cluster = OrderedDict([
            ("cluster", OrderedDict([
                ("certificate-authority-data", "data"),
                ("server", "endpoint")
            ])),
            ("name", "clustername")
        ])            
        correct = OrderedDict([
            ("apiVersion", "v1"),
            ("clusters", [
                OrderedDict([
                    ("cluster", OrderedDict([
                        ("certificate-authority-data", "data"),
                        ("server", "endpoint")
                    ])),
                    ("name", "clustername")
                ])
            ]),
            ("contexts", []),
            ("current-context", None),
            ("kind", "Config"),
            ("preferences", OrderedDict()),
            ("users", [])
        ])
        updated = self._appender.insert_entry(Kubeconfig(None, initial),
                                              "clusters",
                                              cluster)
        self.assertDictEqual(updated.content, correct)

    def test_key_not_exist(self): 
        initial = OrderedDict([
            ("apiVersion", "v1"),
            ("contexts", []),
            ("current-context", None),
            ("kind", "Config"),
            ("preferences", OrderedDict()),
            ("users", [])
        ])
        cluster = OrderedDict([
            ("cluster", OrderedDict([
                ("certificate-authority-data", "data"),
                ("server", "endpoint")
            ])),
            ("name", "clustername")
        ])
        correct = OrderedDict([
            ("apiVersion", "v1"),
            ("contexts", []),
            ("current-context", None),
            ("kind", "Config"),
            ("preferences", OrderedDict()),
            ("users", []),
            ("clusters", [
                OrderedDict([
                    ("cluster", OrderedDict([
                        ("certificate-authority-data", "data"),
                        ("server", "endpoint")
                    ])),
                    ("name", "clustername")
                ])
            ])
        ])
        updated = self._appender.insert_entry(Kubeconfig(None, initial),
                                              "clusters",
                                              cluster)
        self.assertDictEqual(updated.content, correct)

    def test_key_not_array(self):
        initial = OrderedDict([
            ("apiVersion", "v1"),
            ("contexts", []),
            ("current-context", None),
            ("kind", "Config"),
            ("preferences", OrderedDict()),
            ("users", [])
        ])
        cluster = OrderedDict([
            ("cluster", OrderedDict([
                ("certificate-authority-data", "data"),
                ("server", "endpoint")
            ])),
            ("name", "clustername")
        ])
        self.assertRaises(KubeconfigError, 
                          self._appender.insert_entry,
                          Kubeconfig(None, initial),
                          "kind",
                          cluster)

    def test_make_context(self):
        cluster = OrderedDict([
            ("name", "clustername"),
            ("cluster", OrderedDict())
        ])
        user = OrderedDict([
            ("name", "username"),
            ("user", OrderedDict())
        ])
        context_correct = OrderedDict([
            ("context", OrderedDict([
                ("cluster", "clustername"),
                ("user", "username")
            ])),
            ("name", "username")
        ])
        context = self._appender._make_context(cluster, user)
        self.assertDictEqual(context, context_correct)

    def test_make_context_alias(self):
        cluster = OrderedDict([
            ("name", "clustername"),
            ("cluster", OrderedDict())
        ])
        user = OrderedDict([
            ("name", "username"),
            ("user", OrderedDict())
        ])
        context_correct = OrderedDict([
            ("context", OrderedDict([
                ("cluster", "clustername"),
                ("user", "username")
            ])),
            ("name", "alias")
        ])
        alias = "alias"
        context = self._appender._make_context(cluster, user, alias=alias)
        self.assertDictEqual(context, context_correct)
