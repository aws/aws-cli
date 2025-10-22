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
import logging

from botocore.compat import OrderedDict

from awscli.customizations.commands import BasicCommand
from awscli.customizations.utils import uni_print
from awscli.customizations.eks.exceptions import EKSClusterError
from awscli.customizations.eks.kubeconfig import (Kubeconfig,
                                                  KubeconfigError,
                                                  KubeconfigLoader,
                                                  KubeconfigWriter,
                                                  KubeconfigValidator,
                                                  KubeconfigAppender)
from awscli.customizations.eks.ordered_yaml import ordered_yaml_dump
from awscli.utils import create_nested_client

LOG = logging.getLogger(__name__)

DEFAULT_PATH = os.path.expanduser("~/.kube/config")

# At the time EKS no longer supports Kubernetes v1.21 (probably ~Dec 2023),
# this can be safely changed to default to writing "v1"
API_VERSION = "client.authentication.k8s.io/v1beta1"

class UpdateKubeconfigCommand(BasicCommand):
    NAME = 'update-kubeconfig'

    DESCRIPTION = BasicCommand.FROM_FILE(
        'eks',
        'update-kubeconfig',
        '_description.rst'
    )

    ARG_TABLE = [
        {
            'name': 'name',
            'dest': 'cluster_name',
            'help_text': ("The name of the cluster for which "
                          "to create a kubeconfig entry. "
                          "This cluster must exist in your account and in the "
                          "specified or configured default Region "
                          "for your AWS CLI installation."),
            'required': True
        },
        {
            'name': 'kubeconfig',
            'help_text': ("Optionally specify a kubeconfig file to append "
                          "with your configuration. "
                          "By default, the configuration is written to the "
                          "first file path in the KUBECONFIG "
                          "environment variable (if it is set) "
                          "or the default kubeconfig path (.kube/config) "
                          "in your home directory."),
            'required': False
        },
        {
            'name': 'role-arn',
            'help_text': ("To assume a role for cluster authentication, "
                          "specify an IAM role ARN with this option. "
                          "For example, if you created a cluster "
                          "while assuming an IAM role, "
                          "then you must also assume that role to "
                          "connect to the cluster the first time."),
            'required': False
        },
        {
            'name': 'proxy-url',
            'help_text': ("Optionally specify a proxy url to route "
                          "traffic via when connecting to a cluster."),
            'required': False
        },
        {
            'name': 'dry-run',
            'action': 'store_true',
            'default': False,
            'help_text': ("Print the merged kubeconfig to stdout instead of "
                          "writing it to the specified file."),
            'required': False
        },
        {
            'name': 'verbose',
            'action': 'store_true',
            'default': False,
            'help_text': ("Print more detailed output "
                          "when writing to the kubeconfig file, "
                          "including the appended entries.")
        },
        {
            'name': 'alias',
            'help_text': ("Alias for the cluster context name. "
                          "Defaults to match cluster ARN."),
            'required': False
        },
        {
            'name': 'user-alias',
            'help_text': ("Alias for the generated user name. "
                          "Defaults to match cluster ARN."),
            'required': False
        },
        {
            'name': 'assume-role-arn',
            'help_text': ('To assume a role for retrieving cluster information, '
                         'specify an IAM role ARN with this option. '
                         'Use this for cross-account access to get cluster details '
                         'from the account where the cluster resides.'),
            'required': False
        }
    ]

    def _display_entries(self, entries):
        """
        Display entries in yaml format

        :param entries: a list of OrderedDicts to be printed
        :type entries: list
        """
        uni_print("Entries:\n\n")
        for entry in entries:
            uni_print(ordered_yaml_dump(entry))
            uni_print("\n")

    def _run_main(self, parsed_args, parsed_globals):
        client = EKSClient(self._session,
                           parsed_args=parsed_args,
                           parsed_globals=parsed_globals)
        new_cluster_dict = client.get_cluster_entry()
        new_user_dict = client.get_user_entry(user_alias=parsed_args.user_alias)

        config_selector = KubeconfigSelector(
            os.environ.get("KUBECONFIG", ""),
            parsed_args.kubeconfig
        )
        config = config_selector.choose_kubeconfig(
            new_cluster_dict["name"]
        )
        updating_existing = config.has_cluster(new_cluster_dict["name"])
        appender = KubeconfigAppender()
        new_context_dict = appender.insert_cluster_user_pair(config,
                                                             new_cluster_dict,
                                                             new_user_dict,
                                                             parsed_args.alias)

        if parsed_args.dry_run:
            uni_print(config.dump_content())
        else:
            writer = KubeconfigWriter()
            writer.write_kubeconfig(config)

            if updating_existing:
                uni_print("Updated context {0} in {1}\n".format(
                    new_context_dict["name"], config.path
                ))
            else:
                uni_print("Added new context {0} to {1}\n".format(
                    new_context_dict["name"], config.path
                ))

            if parsed_args.verbose:
                self._display_entries([
                    new_context_dict,
                    new_user_dict,
                    new_cluster_dict
                ])



class KubeconfigSelector(object):

    def __init__(self, env_variable, path_in, validator=None,
                                              loader=None):
        """
        Parse KUBECONFIG into a list of absolute paths.
        Also replace the empty list with DEFAULT_PATH

        :param env_variable: KUBECONFIG as a long string
        :type env_variable: string

        :param path_in: The path passed in through the CLI
        :type path_in: string or None
        """
        if validator is None:
            validator = KubeconfigValidator()
        self._validator = validator

        if loader is None:
            loader = KubeconfigLoader(validator)
        self._loader = loader

        if path_in is not None:
            # Override environment variable
            self._paths = [self._expand_path(path_in)]
        else:
            # Get the list of paths from the environment variable
            if env_variable == "":
                env_variable = DEFAULT_PATH
            self._paths = [self._expand_path(element)
                           for element in env_variable.split(os.pathsep)
                           if len(element.strip()) > 0]
            if len(self._paths) == 0:
                self._paths = [DEFAULT_PATH]

    def choose_kubeconfig(self, cluster_name):
        """
        Choose which kubeconfig file to read from.
        If name is already an entry in one of the $KUBECONFIG files,
        choose that one.
        Otherwise choose the first file.

        :param cluster_name: The name of the cluster which is going to be added
        :type cluster_name: String

        :return: a chosen Kubeconfig based on above rules
        :rtype: Kubeconfig
        """
        # Search for an existing entry to update
        for candidate_path in self._paths:
            try:
                loaded_config = self._loader.load_kubeconfig(candidate_path)

                if loaded_config.has_cluster(cluster_name):
                    LOG.debug("Found entry to update at {0}".format(
                        candidate_path
                    ))
                    return loaded_config
            except KubeconfigError as e:
                LOG.warning("Passing {0}:{1}".format(candidate_path, e))

        # No entry was found, use the first file in KUBECONFIG
        #
        # Note: This could raise KubeconfigErrors if paths[0] is corrupted
        return self._loader.load_kubeconfig(self._paths[0])

    def _expand_path(self, path):
        """ A helper to expand a path to a full absolute path. """
        return os.path.abspath(os.path.expanduser(path))


class EKSClient(object):
    def __init__(self, session, parsed_args, parsed_globals=None):
        self._session = session
        self._cluster_name = parsed_args.cluster_name
        self._cluster_description = None
        self._parsed_globals = parsed_globals
        self._parsed_args = parsed_args

    @property
    def cluster_description(self):
        """
        Use an eks describe-cluster call to get the cluster description
        Cache the response in self._cluster_description.
        describe-cluster will only be called once.
        """
        if self._cluster_description is not None:
            return self._cluster_description

        client_kwargs = {}
        if self._parsed_globals:
            client_kwargs.update({
                "region_name": self._parsed_globals.region,
                "endpoint_url": self._parsed_globals.endpoint_url,
                "verify": self._parsed_globals.verify_ssl,
            })

        # Handle role assumption if needed
        if getattr(self._parsed_args, 'assume_role_arn', None):
            sts_client = create_nested_client(self._session, 'sts')
            credentials = sts_client.assume_role(
                RoleArn=self._parsed_args.assume_role_arn,
                RoleSessionName='EKSDescribeClusterSession'
            )["Credentials"]

            client_kwargs.update({
                "aws_access_key_id": credentials["AccessKeyId"],
                "aws_secret_access_key": credentials["SecretAccessKey"],
                "aws_session_token": credentials["SessionToken"],
            })

        client = create_nested_client(self._session, "eks", **client_kwargs)
        full_description = client.describe_cluster(name=self._cluster_name)
        cluster = full_description.get("cluster")

        if not cluster or "status" not in cluster:
            raise EKSClusterError("Cluster not found")
        if cluster["status"] not in ["ACTIVE", "UPDATING"]:
            raise EKSClusterError(f"Cluster status is {cluster['status']}")

        self._cluster_description = cluster
        return cluster

    def get_cluster_entry(self):
        """
        Return a cluster entry generated using
        the previously obtained description.
        """

        cert_data = self.cluster_description.get("certificateAuthority", {}).get("data", "")
        endpoint = self.cluster_description.get("endpoint")
        arn = self.cluster_description.get("arn")

        generated_cluster = OrderedDict([
            ("cluster", OrderedDict([
                ("certificate-authority-data", cert_data),
                ("server", endpoint)
            ])),
            ("name", arn)
        ])

        if self._parsed_args.proxy_url is not None:
            generated_cluster["cluster"]["proxy-url"] = self._parsed_args.proxy_url

        return generated_cluster

    def get_user_entry(self, user_alias=None):
        """
        Return a user entry generated using
        the previously obtained description.
        """
        region = self.cluster_description.get("arn").split(":")[3]
        outpost_config = self.cluster_description.get("outpostConfig")

        if outpost_config is None:
            cluster_identification_parameter = "--cluster-name"
            cluster_identification_value = self._cluster_name
        else:
            # If cluster contains outpostConfig, use id for identification
            cluster_identification_parameter = "--cluster-id"
            cluster_identification_value = self.cluster_description.get("id")

        generated_user = OrderedDict([
            ("name", user_alias or self.cluster_description.get("arn", "")),
            ("user", OrderedDict([
                ("exec", OrderedDict([
                    ("apiVersion", API_VERSION),
                    ("args",
                        [
                            "--region",
                            region,
                            "eks",
                            "get-token",
                            cluster_identification_parameter,
                            cluster_identification_value,
                            "--output",
                            "json",
                        ]),
                    ("command", "aws"),
                ]))
            ]))
        ])

        if self._parsed_args.role_arn is not None:
            generated_user["user"]["exec"]["args"].extend([
                "--role",
                self._parsed_args.role_arn
            ])

        if self._session.profile:
            generated_user["user"]["exec"]["env"] = [OrderedDict([
                ("name", "AWS_PROFILE"),
                ("value", self._session.profile)
            ])]

        return generated_user
