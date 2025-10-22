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
import shutil
import sys
import tempfile
from argparse import Namespace

import botocore
from botocore.compat import OrderedDict

import awscli.customizations.eks.kubeconfig as kubeconfig
from awscli.customizations.eks.exceptions import EKSClusterError, EKSError
from awscli.customizations.eks.ordered_yaml import ordered_yaml_load
from awscli.customizations.eks.update_kubeconfig import (API_VERSION,
                                                         EKSClient,
                                                         KubeconfigSelector)
from awscli.customizations.utils import uni_print
from awscli.testutils import mock, unittest
from tests.functional.eks.test_util import (
    describe_cluster_creating_response, describe_cluster_deleting_response,
    describe_cluster_no_status_response, describe_cluster_response,
    describe_cluster_response_outpost_cluster, get_testdata)


def generate_env_variable(files):
    """
    Generate a string which is an environment variable
    containing the absolute paths for each file in files

    :param files: The names of the files to put in the environment variable
    :type files: list
    """
    output = ""
    for file in files:
        if len(output) == 0:
            output = file
        else:
            output += os.path.pathsep + file
    return output


EXAMPLE_ARN = "arn:aws:eks:region:111222333444:cluster/ExampleCluster"

class TestKubeconfigSelector(unittest.TestCase):
    def setUp(self):
        self._validator = kubeconfig.KubeconfigValidator()
        self._loader = kubeconfig.KubeconfigLoader(self._validator)

    def assert_chosen_path(self,
                           env_variable,
                           path_in,
                           cluster_name,
                           chosen_path):
        selector = KubeconfigSelector(env_variable, path_in, 
                                                    self._validator,
                                                    self._loader)
        self.assertEqual(selector.choose_kubeconfig(cluster_name).path,
                         chosen_path)  

    def test_parse_env_variable(self):
        paths = [
            "",
            "",
            get_testdata("valid_bad_cluster"),
            get_testdata("valid_bad_cluster2"),
            "",
            get_testdata("valid_existing"),
            ""
        ]

        env_variable = generate_env_variable(paths)

        selector = KubeconfigSelector(env_variable, None, self._validator,
                                                          self._loader)
        self.assertEqual(selector._paths, [path for path in paths 
                                                if len(path) > 0])

    def test_choose_env_only(self):
        paths = [
            get_testdata("valid_simple"),
            get_testdata("valid_existing")
        ] + glob.glob(get_testdata("invalid_*")) + [
            get_testdata("valid_bad_context"),
            get_testdata("valid_no_user")
        ]
        env_variable = generate_env_variable(paths)
        self.assert_chosen_path(env_variable, 
                                None, 
                                EXAMPLE_ARN, 
                                get_testdata("valid_simple"))

    def test_choose_existing(self):
        paths = [
            get_testdata("valid_simple"),
            get_testdata("valid_existing")
        ] + glob.glob(get_testdata("invalid_*")) + [
            get_testdata("valid_bad_context"),
            get_testdata("valid_no_user"),
            get_testdata("output_single"),
            get_testdata("output_single_with_role")
        ]
        env_variable = generate_env_variable(paths)
        self.assert_chosen_path(env_variable, 
                                None, 
                                EXAMPLE_ARN, 
                                get_testdata("output_single"))

    def test_arg_override(self):
        paths = [
            get_testdata("valid_simple"),
            get_testdata("valid_existing")
        ] + glob.glob(get_testdata("invalid_*")) + [
            get_testdata("valid_bad_context"),
            get_testdata("valid_no_user"),
            get_testdata("output_single"),
            get_testdata("output_single_with_role")
        ]
        env_variable = generate_env_variable(paths)
        self.assert_chosen_path(env_variable, 
                                get_testdata("output_combined"), 
                                EXAMPLE_ARN, 
                                get_testdata("output_combined"))

    def test_first_corrupted(self):
        paths = glob.glob(get_testdata("invalid_*")) + [
            get_testdata("valid_bad_context"),
            get_testdata("valid_no_user")
        ]
        env_variable = generate_env_variable(paths)
        selector = KubeconfigSelector(env_variable, None, self._validator,
                                                          self._loader)
        self.assertRaises(kubeconfig.KubeconfigCorruptedError, 
                          selector.choose_kubeconfig,
                          EXAMPLE_ARN)

    def test_arg_override_first_corrupted(self):
        paths = glob.glob(get_testdata("invalid_*")) + [
            get_testdata("valid_bad_context"),
            get_testdata("valid_no_user")
        ]
        env_variable = generate_env_variable(paths)
        self.assert_chosen_path(env_variable, 
                                get_testdata("output_combined"), 
                                EXAMPLE_ARN, 
                                get_testdata("output_combined"))

class TestEKSClient(unittest.TestCase):
    def setUp(self):
        self._correct_cluster_entry = OrderedDict([
            ("cluster", OrderedDict([
                ("certificate-authority-data", describe_cluster_response()\
                    ["cluster"]["certificateAuthority"]["data"]),
                ("server", describe_cluster_response()["cluster"]["endpoint"])
            ])),
            ("name", describe_cluster_response()["cluster"]["arn"])
        ])

        self._correct_user_entry = OrderedDict([
            ("name", describe_cluster_response()["cluster"]["arn"]),
            ("user", OrderedDict([
                ("exec", OrderedDict([
                    ("apiVersion", API_VERSION),
                    ("args",
                        [
                            "--region",
                            "region",
                            "eks",
                            "get-token",
                            "--cluster-name",
                            "ExampleCluster",
                            "--output",
                            "json",
                        ]),
                    ("command", "aws")
                ]))
            ]))
        ])

        self._correct_user_entry_outpost_cluster = OrderedDict([
            ("name", describe_cluster_response()["cluster"]["arn"]),
            ("user", OrderedDict([
                ("exec", OrderedDict([
                    ("apiVersion", API_VERSION),
                    ("args",
                        [
                            "--region",
                            "region",
                            "eks",
                            "get-token",
                            "--cluster-id",
                            "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                            "--output",
                            "json",
                        ]),
                    ("command", "aws")
                ]))
            ]))
        ])

        self._mock_client = mock.Mock()
        self._mock_client.describe_cluster.return_value =\
                                                    describe_cluster_response()

        self._session = mock.Mock(spec=botocore.session.Session)
        self._session.create_client.return_value = self._mock_client
        self._session.profile = None

        self._client = EKSClient(self._session, parsed_args=Namespace(cluster_name="ExampleCluster", role_arn=None, proxy_url=None))

    def test_get_cluster_description(self):
        self.assertEqual(self._client.cluster_description,
                         describe_cluster_response()["cluster"])
        self._mock_client.describe_cluster.assert_called_once_with(
            name="ExampleCluster"
        )
        self._session.create_client.assert_called_once_with("eks")

    def test_get_cluster_description_no_status(self):
        self._mock_client.describe_cluster.return_value = \
            describe_cluster_no_status_response()
        with self.assertRaises(EKSClusterError):
            self._client.cluster_description
        self._mock_client.describe_cluster.assert_called_once_with(
            name="ExampleCluster"
        )
        self._session.create_client.assert_called_once_with("eks")

    def test_get_cluster_entry(self):
        self.assertEqual(self._client.get_cluster_entry(),
                         self._correct_cluster_entry)
        self._mock_client.describe_cluster.assert_called_once_with(
            name="ExampleCluster"
        )
        self._session.create_client.assert_called_once_with("eks")

    def test_get_cluster_entry_with_proxy_url_passed(self):
        proxy_url = "https://myproxy.com"
        correct_cluster_entry_with_proxy_url = OrderedDict([
            ("cluster", OrderedDict([
                ("certificate-authority-data", describe_cluster_response()\
                    ["cluster"]["certificateAuthority"]["data"]),
                ("server", describe_cluster_response()["cluster"]["endpoint"]),
                ("proxy-url", proxy_url)
            ])),
            ("name", describe_cluster_response()["cluster"]["arn"])
        ])
        client = EKSClient(self._session, parsed_args=Namespace(cluster_name="ProxiedCluster", 
                                                                role_arn=None, 
                                                                proxy_url=proxy_url))        
        self.assertEqual(client.get_cluster_entry(), 
                         correct_cluster_entry_with_proxy_url)
        self._mock_client.describe_cluster.assert_called_once_with(
            name="ProxiedCluster"
        )
        self._session.create_client.assert_called_once_with("eks")

    def test_get_user_entry(self):
        self.assertEqual(self._client.get_user_entry(),
                         self._correct_user_entry)
        self._mock_client.describe_cluster.assert_called_once_with(
            name="ExampleCluster"
        )
        self._session.create_client.assert_called_once_with("eks")

    def test_get_user_entry_outpost_cluster(self):
        self._mock_client.describe_cluster.return_value =\
                                                    describe_cluster_response_outpost_cluster()
        self.assertEqual(self._client.get_user_entry(),
                         self._correct_user_entry_outpost_cluster)
        self._mock_client.describe_cluster.assert_called_once_with(
            name="ExampleCluster"
        )
        self._session.create_client.assert_called_once_with("eks") 

    def test_get_both(self):
        self.assertEqual(self._client.get_cluster_entry(),
                         self._correct_cluster_entry)
        self.assertEqual(self._client.get_user_entry(),
                         self._correct_user_entry)
        self._mock_client.describe_cluster.assert_called_once_with(
            name="ExampleCluster"
        )
        self._session.create_client.assert_called_once_with("eks")

    def test_cluster_creating(self):
        self._mock_client.describe_cluster.return_value =\
                                           describe_cluster_creating_response()
        with self.assertRaises(EKSClusterError):
            self._client.cluster_description
        self._mock_client.describe_cluster.assert_called_once_with(
            name="ExampleCluster"
        )
        self._session.create_client.assert_called_once_with("eks")

    def test_cluster_deleting(self):
        self._mock_client.describe_cluster.return_value =\
                                           describe_cluster_deleting_response()
        with self.assertRaises(EKSClusterError):
            self._client.cluster_description
        self._mock_client.describe_cluster.assert_called_once_with(
            name="ExampleCluster"
        )
        self._session.create_client.assert_called_once_with("eks")

    def test_profile(self):
        self._session.profile = "profile"
        self._correct_user_entry["user"]["exec"]["env"] = [
            OrderedDict([
                ("name", "AWS_PROFILE"),
                ("value", "profile")
            ])
        ]
        self.assertEqual(self._client.get_user_entry(),
                         self._correct_user_entry)
        self._mock_client.describe_cluster.assert_called_once_with(
            name="ExampleCluster"
        )
        self._session.create_client.assert_called_once_with("eks")

    def test_create_user_with_alias(self):
        self._correct_user_entry["name"] = "alias"
        self.assertEqual(self._client.get_user_entry(user_alias="alias"),
                         self._correct_user_entry)
        self._mock_client.describe_cluster.assert_called_once_with(
            name="ExampleCluster"
        )
        self._session.create_client.assert_called_once_with("eks")

    def test_create_user_without_alias(self):
        self.assertEqual(self._client.get_user_entry(),
                         self._correct_user_entry)
        self._mock_client.describe_cluster.assert_called_once_with(
            name="ExampleCluster"
        )
        self._session.create_client.assert_called_once_with("eks")
