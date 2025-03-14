# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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

import logging, json, sys
import botocore

from awscli.customizations.commands import BasicCommand
from awscli.customizations.emrcontainers.constants import (
    SERVICE_ACCOUNT_NAMING,
    ServiceAccount,
)
from awscli.customizations.emrcontainers.base36 import Base36
from awscli.customizations.emrcontainers.eks import EKS
from awscli.customizations.utils import uni_print
from awscli.customizations.emrcontainers.utils import get_region

LOG = logging.getLogger(__name__)


class DeleteRoleAssociationsCommand(BasicCommand):
    NAME = "delete-role-associations"

    DESCRIPTION = BasicCommand.FROM_FILE(
        "emr-containers", "delete-role-associations", "_description.rst"
    )

    ARG_TABLE = [
        {
            "name": "cluster-name",
            "help_text": (
                "Specify the name of the Amazon EKS cluster with "
                "which the IAM Role would be dissociated."
            ),
            "required": True,
        },
        {
            "name": "namespace",
            "help_text": (
                "Specify the job/application namespace from the Amazon EKS cluster "
                "with which the IAM Role would be dissociated."
            ),
            "required": True,
        },
        {
            "name": "role-name",
            "help_text": (
                "Specify the IAM Role name that you want to dissociate "
                "with Amazon EMR on EKS."
            ),
            "required": True,
        },
        {
            "name": "type",
            "help_text": (
                "Specify the Amazon EMR on EKS submission model and choose service accounts that you want to "
                "dissociate from Amazon EMR on EKS. The default is start_job_run. Supported types: start_job_run, "
                "interactive_endpoint, spark_operator, flink_operator, livy."
            ),
            "required": False,
            "choices": [
                "start_job_run",
                "interactive_endpoint",
                "spark_operator",
                "flink_operator",
                "livy",
            ],
        },
        {
            "name": "operator-namespace",
            "help_text": (
                "Specify the namespace under which you want to dissociate the operator service account "
                "from the IAM role. Default to the job/application namespace specified. Note: If jobs are running "
                "in a different namespace than the operator installation namespace, this parameter needs to be set as "
                "the namespace that the operator is running on."
            ),
            "required": False,
        },
        {
            "name": "service-account-name",
            "help_text": (
                "Specify the service account name that you want to dissociate with the IAM role. "
                "By default, Amazon EMR on EKS service accounts will be used for association."
            ),
            "required": False,
        },
    ]

    def _run_main(self, parsed_args, parsed_globals):
        """Call to run the commands"""

        self._cluster_name = parsed_args.cluster_name
        self._namespace = parsed_args.namespace
        self._role_name = parsed_args.role_name
        self._type = parsed_args.type or "start_job_run"
        self._operator_namespace = parsed_args.operator_namespace
        self._service_account_name = parsed_args.service_account_name
        self._region = get_region(self._session, parsed_globals)

        result = self._delete_role_associations(parsed_globals)
        if result:
            uni_print(json.dumps(result, indent=4))

        return 0

    def _delete_role_associations(self, parsed_globals):
        """Method to delete role associations if not done already"""
        eks_client = EKS(
            self._session.create_client(
                "eks",
                region_name=self._region,
                verify=parsed_globals.verify_ssl,
            )
        )
        account_id = eks_client.get_account_id(self._cluster_name)

        results = []
        # If service account provided, delete association with provided service account and role
        if self._service_account_name:
            service_account_namespace_mapping = [
                (self._service_account_name, self._namespace)
            ]
        else:
            # By default, delete associations with EMR on EKS service accounts
            base36 = Base36()

            base36_encoded_role_name = base36.encode(self._role_name)
            LOG.debug(f"Base36 encoded role name: {base36_encoded_role_name}")
            service_account_namespace_mapping = (
                self._get_emr_service_account_namespace_mapping(
                    account_id, base36_encoded_role_name
                )
            )

        for (
            service_account_name,
            namespace,
        ) in service_account_namespace_mapping:
            try:
                association = eks_client.list_pod_identity_associations(
                    self._cluster_name, namespace, service_account_name
                )
                if not association.get("associations", []):
                    uni_print(
                        f"Skipping deletion as no pod identity association found for service account {service_account_name} "
                        f"and role {self._role_name} in namespace {namespace}\n",
                        out_file=sys.stderr,
                    )
                    continue
                association_id = association["associations"][0][
                    "associationId"
                ]
                LOG.debug(
                    f"Deleting pod identity association for service account {service_account_name} "
                    f"and role {self._role_name} in {namespace} with association id {association_id}"
                )
                result = eks_client.delete_pod_identity_association(
                    self._cluster_name, association_id
                )
                results.append(
                    result["association"]
                    if "association" in result
                    else result
                )
            except botocore.exceptions.ClientError as error:
                raise Exception(
                    f"Failed to delete pod identity association for service account {service_account_name}, "
                    f"role {self._role_name} in namespace {namespace}: {error.response['Error']['Message']}"
                ) from error
        return results

    def _get_emr_service_account_namespace_mapping(
        self, account_id, base36_encoded_role_name
    ):
        return getattr(self, f"_get_{self._type}_mapping")(
            account_id, base36_encoded_role_name
        )

    def _get_start_job_run_mapping(self, account_id, base36_encoded_role_name):
        emr_spark_components = ["client", "driver", "executor"]
        return [
            (
                SERVICE_ACCOUNT_NAMING
                % {
                    "FRAMEWORK": "spark",
                    "COMPONENT": component,
                    "AWS_ACCOUNT_ID": account_id,
                    "BASE36_ENCODED_ROLE_NAME": base36_encoded_role_name,
                },
                self._namespace,
            )
            for component in emr_spark_components
        ]

    def _get_interactive_endpoint_mapping(
        self, account_id, base36_encoded_role_name
    ):
        emr_spark_endpoint_components = ["jeg", "jeg-kernel", "session"]
        return [
            (
                SERVICE_ACCOUNT_NAMING
                % {
                    "FRAMEWORK": "spark",
                    "COMPONENT": component,
                    "AWS_ACCOUNT_ID": account_id,
                    "BASE36_ENCODED_ROLE_NAME": base36_encoded_role_name,
                },
                self._namespace,
            )
            for component in emr_spark_endpoint_components
        ]

    def _get_spark_operator_mapping(
        self, account_id, base36_encoded_role_name
    ):
        emr_spark_operator_components = ["driver", "executor"]
        service_accounts = [
            (
                ServiceAccount.SPARK_OPERATOR_SERVICE_ACCOUNT.value,
                (
                    self._operator_namespace
                    if self._operator_namespace
                    else self._namespace
                ),
            )
        ]
        service_accounts.extend(
            [
                (
                    SERVICE_ACCOUNT_NAMING
                    % {
                        "FRAMEWORK": "spark",
                        "COMPONENT": component,
                        "AWS_ACCOUNT_ID": account_id,
                        "BASE36_ENCODED_ROLE_NAME": base36_encoded_role_name,
                    },
                    self._namespace,
                )
                for component in emr_spark_operator_components
            ]
        )
        return service_accounts

    def _get_flink_operator_mapping(
        self, account_id, base36_encoded_role_name
    ):
        emr_flink_operator_components = ["jobmanager", "taskmanager"]
        service_accounts = [
            (
                ServiceAccount.FLINK_OPERATOR_SERVICE_ACCOUNT.value,
                (
                    self._operator_namespace
                    if self._operator_namespace
                    else self._namespace
                ),
            )
        ]
        service_accounts.extend(
            [
                (
                    SERVICE_ACCOUNT_NAMING
                    % {
                        "FRAMEWORK": "flink",
                        "COMPONENT": component,
                        "AWS_ACCOUNT_ID": account_id,
                        "BASE36_ENCODED_ROLE_NAME": base36_encoded_role_name,
                    },
                    self._namespace,
                )
                for component in emr_flink_operator_components
            ]
        )
        return service_accounts

    def _get_livy_mapping(self, account_id, base36_encoded_role_name):
        return [
            (
                ServiceAccount.LIVY_SERVICE_ACCOUNT.value,
                (
                    self._operator_namespace
                    if self._operator_namespace
                    else self._namespace
                ),
            ),
            (ServiceAccount.LIVY_SPARK_SERVICE_ACCOUNT.value, self._namespace),
        ]
