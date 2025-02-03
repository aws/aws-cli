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
from tests import HTTPResponse


class TestDeleteRoleAssociationsCommand:
    def assert_list_call_matches(
        self, aws_request, service_account, cluster_name, namespace
    ):
        assert aws_request.service_name == "eks"
        assert aws_request.operation_name == "ListPodIdentityAssociations"
        assert aws_request.params["clusterName"] == cluster_name
        assert aws_request.params["namespace"] == namespace
        assert aws_request.params["serviceAccount"] == service_account

    def assert_delete_call_matches(
        self, aws_request, cluster_name, association_id
    ):
        assert aws_request.service_name == "eks"
        assert aws_request.operation_name == "DeletePodIdentityAssociation"
        assert aws_request.params["clusterName"] == cluster_name
        assert aws_request.params["associationId"] == association_id

    # Use case: Expect to return delete pod identity association results for start job run
    # Expected results: Operation is performed by client
    # to delete pod identity associations with start job run service accounts
    def test_delete_role_associations_for_start_job_run(
        self,
        cli_runner,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        list_pod_identity_association_response,
        delete_pod_identity_association_response,
        start_job_run_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        for i in range(3):
            cli_runner.add_response(
                HTTPResponse(body=list_pod_identity_association_response[i])
            )
            cli_runner.add_response(
                HTTPResponse(body=delete_pod_identity_association_response[i])
            )

        result = cli_runner.run(
            [
                "emr-containers",
                "delete-role-associations",
                "--cluster-name",
                cluster_name,
                "--namespace",
                namespace,
                "--role-name",
                role_name,
            ]
        )

        request_idx = 0
        assert result.aws_requests[request_idx].service_name == "eks"
        assert (
            result.aws_requests[request_idx].operation_name == "DescribeCluster"
        )
        for i in range(len(start_job_run_service_accounts)):
            request_idx += 1
            self.assert_list_call_matches(
                result.aws_requests[request_idx],
                start_job_run_service_accounts[i],
                cluster_name,
                namespace,
            )
            request_idx += 1
            self.assert_delete_call_matches(
                result.aws_requests[request_idx], cluster_name, str(i + 1)
            )

    # Use case: Expect to return delete pod identity association results for interactive endpoint
    # Expected results: Operation is performed by client
    # to delete pod identity associations with interactive endpoint service accounts
    def test_delete_role_associations_for_interactive_endpoint(
        self,
        cli_runner,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        list_pod_identity_association_response,
        delete_pod_identity_association_response,
        interactive_endpoint_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        for i in range(3):
            cli_runner.add_response(
                HTTPResponse(body=list_pod_identity_association_response[i])
            )
            cli_runner.add_response(
                HTTPResponse(body=delete_pod_identity_association_response[i])
            )

        result = cli_runner.run(
            [
                "emr-containers",
                "delete-role-associations",
                "--cluster-name",
                cluster_name,
                "--namespace",
                namespace,
                "--role-name",
                role_name,
                "--type",
                "interactive_endpoint",
            ]
        )

        request_idx = 0
        assert result.aws_requests[request_idx].service_name == "eks"
        assert (
            result.aws_requests[request_idx].operation_name == "DescribeCluster"
        )
        for i in range(len(interactive_endpoint_service_accounts)):
            request_idx += 1
            self.assert_list_call_matches(
                result.aws_requests[request_idx],
                interactive_endpoint_service_accounts[i],
                cluster_name,
                namespace,
            )
            request_idx += 1
            self.assert_delete_call_matches(
                result.aws_requests[request_idx], cluster_name, str(i + 1)
            )

    # Use case: Expect to return delete pod identity association results for spark operator
    # Expected results: Operation is performed by client
    # to delete pod identity associations with spark operator service accounts
    def test_delete_role_associations_for_spark_operator(
        self,
        cli_runner,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        list_pod_identity_association_response,
        delete_pod_identity_association_response,
        spark_operator_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        for i in range(3):
            cli_runner.add_response(
                HTTPResponse(body=list_pod_identity_association_response[i])
            )
            cli_runner.add_response(
                HTTPResponse(body=delete_pod_identity_association_response[i])
            )

        result = cli_runner.run(
            [
                "emr-containers",
                "delete-role-associations",
                "--cluster-name",
                cluster_name,
                "--namespace",
                namespace,
                "--role-name",
                role_name,
                "--type",
                "spark_operator",
            ]
        )

        request_idx = 0
        assert result.aws_requests[request_idx].service_name == "eks"
        assert (
            result.aws_requests[request_idx].operation_name == "DescribeCluster"
        )
        for i in range(len(spark_operator_service_accounts)):
            request_idx += 1
            self.assert_list_call_matches(
                result.aws_requests[request_idx],
                spark_operator_service_accounts[i],
                cluster_name,
                namespace,
            )
            request_idx += 1
            self.assert_delete_call_matches(
                result.aws_requests[request_idx], cluster_name, str(i + 1)
            )

    # Use case: Expect to return delete pod identity association results for spark operator with operator namespace
    # Expected results: Operation is performed by client
    # to delete pod identity associations with spark operator service accounts in correct namespaces
    def test_delete_role_associations_for_spark_operator_namespace(
        self,
        cli_runner,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        list_pod_identity_association_response,
        delete_pod_identity_association_response,
        spark_operator_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        for i in range(3):
            cli_runner.add_response(
                HTTPResponse(body=list_pod_identity_association_response[i])
            )
            cli_runner.add_response(
                HTTPResponse(body=delete_pod_identity_association_response[i])
            )

        result = cli_runner.run(
            [
                "emr-containers",
                "delete-role-associations",
                "--cluster-name",
                cluster_name,
                "--namespace",
                namespace,
                "--role-name",
                role_name,
                "--type",
                "spark_operator",
                "--operator-namespace",
                "spark-operator",
            ]
        )

        request_idx = 0
        assert result.aws_requests[request_idx].service_name == "eks"
        assert (
            result.aws_requests[request_idx].operation_name == "DescribeCluster"
        )
        for i in range(len(spark_operator_service_accounts)):
            request_idx += 1
            ns = "spark-operator" if i == 0 else namespace
            self.assert_list_call_matches(
                result.aws_requests[request_idx],
                spark_operator_service_accounts[i],
                cluster_name,
                ns,
            )
            request_idx += 1
            self.assert_delete_call_matches(
                result.aws_requests[request_idx], cluster_name, str(i + 1)
            )

    # Use case: Expect to return delete pod identity association results for flink operator
    # Expected results: Operation is performed by client
    # to delete pod identity associations with flink operator service accounts
    def test_delete_role_associations_for_flink_operator(
        self,
        cli_runner,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        list_pod_identity_association_response,
        delete_pod_identity_association_response,
        flink_operator_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        for i in range(3):
            cli_runner.add_response(
                HTTPResponse(body=list_pod_identity_association_response[i])
            )
            cli_runner.add_response(
                HTTPResponse(body=delete_pod_identity_association_response[i])
            )

        result = cli_runner.run(
            [
                "emr-containers",
                "delete-role-associations",
                "--cluster-name",
                cluster_name,
                "--namespace",
                namespace,
                "--role-name",
                role_name,
                "--type",
                "flink_operator",
            ]
        )

        request_idx = 0
        assert result.aws_requests[request_idx].service_name == "eks"
        assert (
            result.aws_requests[request_idx].operation_name == "DescribeCluster"
        )
        for i in range(len(flink_operator_service_accounts)):
            request_idx += 1
            self.assert_list_call_matches(
                result.aws_requests[request_idx],
                flink_operator_service_accounts[i],
                cluster_name,
                namespace,
            )
            request_idx += 1
            self.assert_delete_call_matches(
                result.aws_requests[request_idx], cluster_name, str(i + 1)
            )

    # Use case: Expect to return delete pod identity association results for flink operator with operator namespaces
    # Expected results: Operation is performed by client
    # to delete pod identity associations with flink operator service accounts in correct namespace
    def test_delete_role_associations_for_flink_operator_namespace(
        self,
        cli_runner,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        list_pod_identity_association_response,
        delete_pod_identity_association_response,
        flink_operator_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        for i in range(3):
            cli_runner.add_response(
                HTTPResponse(body=list_pod_identity_association_response[i])
            )
            cli_runner.add_response(
                HTTPResponse(body=delete_pod_identity_association_response[i])
            )

        result = cli_runner.run(
            [
                "emr-containers",
                "delete-role-associations",
                "--cluster-name",
                cluster_name,
                "--namespace",
                namespace,
                "--role-name",
                role_name,
                "--type",
                "flink_operator",
                "--operator-namespace",
                "flink-operator",
            ]
        )

        request_idx = 0
        assert result.aws_requests[request_idx].service_name == "eks"
        assert (
            result.aws_requests[request_idx].operation_name == "DescribeCluster"
        )
        for i in range(len(flink_operator_service_accounts)):
            request_idx += 1
            ns = "flink-operator" if i == 0 else namespace
            self.assert_list_call_matches(
                result.aws_requests[request_idx],
                flink_operator_service_accounts[i],
                cluster_name,
                ns,
            )
            request_idx += 1
            self.assert_delete_call_matches(
                result.aws_requests[request_idx], cluster_name, str(i + 1)
            )

    # Use case: Expect to return delete pod identity association results for livy
    # Expected results: Operation is performed by client
    # to delete pod identity associations with livy service accounts
    def test_delete_role_associations_for_livy(
        self,
        cli_runner,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        list_pod_identity_association_response,
        delete_pod_identity_association_response,
        livy_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        for i in range(2):
            cli_runner.add_response(
                HTTPResponse(body=list_pod_identity_association_response[i])
            )
            cli_runner.add_response(
                HTTPResponse(body=delete_pod_identity_association_response[i])
            )

        result = cli_runner.run(
            [
                "emr-containers",
                "delete-role-associations",
                "--cluster-name",
                cluster_name,
                "--namespace",
                namespace,
                "--role-name",
                role_name,
                "--type",
                "livy",
            ]
        )

        request_idx = 0
        assert result.aws_requests[request_idx].service_name == "eks"
        assert (
            result.aws_requests[request_idx].operation_name == "DescribeCluster"
        )
        for i in range(len(livy_service_accounts)):
            request_idx += 1
            self.assert_list_call_matches(
                result.aws_requests[request_idx],
                livy_service_accounts[i],
                cluster_name,
                namespace,
            )
            request_idx += 1
            self.assert_delete_call_matches(
                result.aws_requests[request_idx], cluster_name, str(i + 1)
            )

    # Use case: Expect to return delete pod identity association results for livy with controller namespace
    # Expected results: Operation is performed by client
    # to delete pod identity associations with livy service accounts in correct namespace
    def test_delete_role_associations_for_livy_namespace(
        self,
        cli_runner,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        list_pod_identity_association_response,
        delete_pod_identity_association_response,
        livy_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        for i in range(2):
            cli_runner.add_response(
                HTTPResponse(body=list_pod_identity_association_response[i])
            )
            cli_runner.add_response(
                HTTPResponse(body=delete_pod_identity_association_response[i])
            )

        result = cli_runner.run(
            [
                "emr-containers",
                "delete-role-associations",
                "--cluster-name",
                cluster_name,
                "--namespace",
                namespace,
                "--role-name",
                role_name,
                "--type",
                "livy",
                "--operator-namespace",
                "livy",
            ]
        )

        request_idx = 0
        assert result.aws_requests[request_idx].service_name == "eks"
        assert (
            result.aws_requests[request_idx].operation_name == "DescribeCluster"
        )
        for i in range(len(livy_service_accounts)):
            request_idx += 1
            ns = "livy" if i == 0 else namespace
            self.assert_list_call_matches(
                result.aws_requests[request_idx],
                livy_service_accounts[i],
                cluster_name,
                ns,
            )
            request_idx += 1
            self.assert_delete_call_matches(
                result.aws_requests[request_idx], cluster_name, str(i + 1)
            )

    # Use case: Expect to return delete pod identity association results for customer input service accounts
    # Expected results: Operation is performed by client
    # to delete pod identity associations with customer input service accounts
    def test_delete_role_associations_for_customer_service_account(
        self,
        cli_runner,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        list_pod_identity_association_response,
        delete_pod_identity_association_response,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        cli_runner.add_response(
            HTTPResponse(body=list_pod_identity_association_response[0])
        )
        cli_runner.add_response(
            HTTPResponse(body=delete_pod_identity_association_response[0])
        )

        result = cli_runner.run(
            [
                "emr-containers",
                "delete-role-associations",
                "--cluster-name",
                cluster_name,
                "--namespace",
                namespace,
                "--role-name",
                role_name,
                "--service-account-name",
                "test_sa",
            ]
        )

        assert result.aws_requests[0].service_name == "eks"
        assert result.aws_requests[0].operation_name == "DescribeCluster"
        self.assert_list_call_matches(
            result.aws_requests[1], "test_sa", cluster_name, namespace
        )
        self.assert_delete_call_matches(
            result.aws_requests[2], cluster_name, "1"
        )

    # Use case: Expect to do nothing on deletion when resource not found but print warning message
    # Expected results: Association deletions are skipped
    def test_create_role_associations_already_exists_for_start_job_run(
        self,
        cli_runner,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        start_job_run_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        cli_runner.add_response(HTTPResponse(body=[]))
        cli_runner.add_response(HTTPResponse(body=[]))
        cli_runner.add_response(HTTPResponse(body=[]))
        result = cli_runner.run(
            [
                "emr-containers",
                "delete-role-associations",
                "--cluster-name",
                cluster_name,
                "--namespace",
                namespace,
                "--role-name",
                role_name,
            ]
        )

        expected_out = ""
        for service_account in start_job_run_service_accounts:
            expected_out += (
                f"Skipping deletion as no pod identity association found for service account {service_account} "
                + f"and role {role_name} in namespace {namespace}\n"
            )
        assert result.stderr == expected_out
