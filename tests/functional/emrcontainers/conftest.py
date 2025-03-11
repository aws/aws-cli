# Copyright 2025 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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
import pytest

from awscli.customizations.emrcontainers.base36 import Base36
from awscli.customizations.emrcontainers.constants import (
    SERVICE_ACCOUNT_NAMING,
    ServiceAccount,
)
from tests import CLIRunner, SessionStubber


@pytest.fixture
def session_stubber():
    return SessionStubber()


@pytest.fixture
def region():
    return "us-west-2"


@pytest.fixture
def cli_runner(session_stubber, region):
    cli_runner = CLIRunner(session_stubber=session_stubber)
    cli_runner.env["AWS_DEFAULT_REGION"] = region
    return cli_runner


@pytest.fixture
def account_id():
    return "123456789012"


@pytest.fixture
def cluster_name():
    return "test-cluster"


@pytest.fixture
def namespace():
    return "test"


@pytest.fixture
def role_name():
    return "myrole"


@pytest.fixture
def role_arn(account_id, role_name):
    return f"arn:aws:iam::{account_id}:role/{role_name}"


@pytest.fixture
def base36_encoded_role_name(role_name):
    return Base36().encode(role_name)


## StartJobRun expected service accounts
@pytest.fixture
def start_job_run_service_accounts(account_id, base36_encoded_role_name):
    emr_spark_components = ["client", "driver", "executor"]
    return [
        SERVICE_ACCOUNT_NAMING
        % {
            "FRAMEWORK": "spark",
            "COMPONENT": component,
            "AWS_ACCOUNT_ID": account_id,
            "BASE36_ENCODED_ROLE_NAME": base36_encoded_role_name,
        }
        for component in emr_spark_components
    ]


## InteractiveEndpoint expected service accounts
@pytest.fixture
def interactive_endpoint_service_accounts(account_id, base36_encoded_role_name):
    emr_spark_components = ["jeg", "jeg-kernel", "session"]
    return [
        SERVICE_ACCOUNT_NAMING
        % {
            "FRAMEWORK": "spark",
            "COMPONENT": component,
            "AWS_ACCOUNT_ID": account_id,
            "BASE36_ENCODED_ROLE_NAME": base36_encoded_role_name,
        }
        for component in emr_spark_components
    ]


## SparkOperator expected service accounts
@pytest.fixture
def spark_operator_service_accounts(account_id, base36_encoded_role_name):
    emr_spark_operator_components = ["driver", "executor"]
    spark_operator_service_accounts = [
        ServiceAccount.SPARK_OPERATOR_SERVICE_ACCOUNT.value
    ]
    spark_operator_service_accounts.extend(
        [
            SERVICE_ACCOUNT_NAMING
            % {
                "FRAMEWORK": "spark",
                "COMPONENT": component,
                "AWS_ACCOUNT_ID": account_id,
                "BASE36_ENCODED_ROLE_NAME": base36_encoded_role_name,
            }
            for component in emr_spark_operator_components
        ]
    )
    return spark_operator_service_accounts


## FlinkOperator expected service accounts
@pytest.fixture
def flink_operator_service_accounts(account_id, base36_encoded_role_name):
    emr_flink_operator_components = ["jobmanager", "taskmanager"]
    flink_operator_service_accounts = [
        ServiceAccount.FLINK_OPERATOR_SERVICE_ACCOUNT.value
    ]
    flink_operator_service_accounts.extend(
        [
            SERVICE_ACCOUNT_NAMING
            % {
                "FRAMEWORK": "flink",
                "COMPONENT": component,
                "AWS_ACCOUNT_ID": account_id,
                "BASE36_ENCODED_ROLE_NAME": base36_encoded_role_name,
            }
            for component in emr_flink_operator_components
        ]
    )
    return flink_operator_service_accounts


## Livy expected service accounts
@pytest.fixture
def livy_service_accounts():
    return [
        ServiceAccount.LIVY_SERVICE_ACCOUNT.value,
        ServiceAccount.LIVY_SPARK_SERVICE_ACCOUNT.value,
    ]


@pytest.fixture
def create_pod_identity_association_response():
    return b'{"association": {"associationId": "a-12345678", "clusterName": "test-cluster", "namespace": "namespace", "serviceAccount":"dummy"}}'


@pytest.fixture
def describe_cluster_response():
    return b'{"cluster": {"arn": "arn:aws:eks:us-west-2:123456789012:cluster/test-cluster"}}'


@pytest.fixture
def list_pod_identity_association_response():
    return [
        b'{"associations":[{"associationId": "1", "clusterName": "test-cluster", "namespace": "namespace", "serviceAccount":"dummy1"}]}',
        b'{"associations":[{"associationId": "2", "clusterName": "test-cluster", "namespace": "namespace", "serviceAccount":"dummy2"}]}',
        b'{"associations":[{"associationId": "3", "clusterName": "test-cluster", "namespace": "namespace", "serviceAccount":"dummy3"}]}',
    ]


@pytest.fixture
def delete_pod_identity_association_response():
    return [
        b'{"association": {"association_id": "1", "clusterName": "test-cluster", "namespace": "namespace", "serviceAccount":"dummy1"}}',
        b'{"association": {"association_id": "2", "clusterName": "test-cluster", "namespace": "namespace", "serviceAccount":"dummy2"}}',
        b'{"association": {"association_id": "3", "clusterName": "test-cluster", "namespace": "namespace", "serviceAccount":"dummy3"}}',
    ]


@pytest.fixture
def create_pod_identity_association_already_exists_error_response():
    return b'{"Code": "ResourceInUseException","Message": "An error occurred (ResourceInUseException) when calling the CreatePodIdentityAssociation operation: Association already exists: a-1"}'


@pytest.fixture
def create_pod_identity_association_other_error_response():
    return b'{"Code": "InvliadRequestException","Message": "Bad Request!"}'
