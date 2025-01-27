# Copyright 2024 Amazon.com, Inc. or its affiliates. All Rights Reserved.
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


class TestCreateRoleAssociationsCommand:
    def assert_call_matches(
        self, aws_request, service_account, cluster_name, namespace, role_arn
    ):
        assert aws_request.service_name == "eks"
        assert aws_request.operation_name == "CreatePodIdentityAssociation"
        assert aws_request.params["clusterName"] == cluster_name
        assert aws_request.params["namespace"] == namespace
        assert aws_request.params["roleArn"] == role_arn
        assert aws_request.params["serviceAccount"] == service_account

    def assert_roll_back(self, aws_request, cluster_name, associationId):
        assert aws_request.service_name == "eks"
        assert aws_request.operation_name == "DeletePodIdentityAssociation"
        assert aws_request.params["clusterName"] == cluster_name
        assert aws_request.params["associationId"] == associationId

    # Use case: Expect to return create pod identity association results for start job run
    # Expected results: Operation is performed by client
    # to create pod identity associations with start job run service accounts
    def test_create_role_associations_for_start_job_run(
        self,
        cli_runner,
        role_arn,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        create_pod_identity_association_response,
        start_job_run_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        result = cli_runner.run(
            [
                "emr-containers",
                "create-role-associations",
                "--cluster-name",
                cluster_name,
                "--namespace",
                namespace,
                "--role-name",
                role_name,
            ]
        )

        assert result.aws_requests[0].service_name == "eks"
        assert result.aws_requests[0].operation_name == "DescribeCluster"
        for i in range(len(start_job_run_service_accounts)):
            self.assert_call_matches(
                result.aws_requests[i + 1],
                start_job_run_service_accounts[i],
                cluster_name,
                namespace,
                role_arn,
            )

    # Use case: Expect to return create pod identity association results for interactive endpoint
    # Expected results: Operation is performed by client
    # to create pod identity associations with interactive endpoint service accounts
    def test_create_role_associations_for_interactive_endpoint(
        self,
        cli_runner,
        role_arn,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        create_pod_identity_association_response,
        interactive_endpoint_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        result = cli_runner.run(
            [
                "emr-containers",
                "create-role-associations",
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

        assert result.aws_requests[0].service_name == "eks"
        assert result.aws_requests[0].operation_name == "DescribeCluster"
        for i in range(len(interactive_endpoint_service_accounts)):
            self.assert_call_matches(
                result.aws_requests[i + 1],
                interactive_endpoint_service_accounts[i],
                cluster_name,
                namespace,
                role_arn,
            )

    # Use case: Expect to return create pod identity association results for spark operator
    # Expected results: Operation is performed by client
    # to create pod identity associations with spark operator service accounts
    def test_create_role_associations_for_spark_operator(
        self,
        cli_runner,
        role_arn,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        create_pod_identity_association_response,
        spark_operator_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        result = cli_runner.run(
            [
                "emr-containers",
                "create-role-associations",
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

        assert result.aws_requests[0].service_name == "eks"
        assert result.aws_requests[0].operation_name == "DescribeCluster"
        for i in range(len(spark_operator_service_accounts)):
            self.assert_call_matches(
                result.aws_requests[i + 1],
                spark_operator_service_accounts[i],
                cluster_name,
                namespace,
                role_arn,
            )

    # Use case: Expect to return create pod identity association results for spark operator with operator namespace
    # Expected results: Operation is performed by client
    # to create pod identity associations with spark operator service accounts in correct namespaces
    def test_create_role_associations_for_spark_operator_namespace(
        self,
        cli_runner,
        role_arn,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        create_pod_identity_association_response,
        spark_operator_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        result = cli_runner.run(
            [
                "emr-containers",
                "create-role-associations",
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

        assert result.aws_requests[0].service_name == "eks"
        assert result.aws_requests[0].operation_name == "DescribeCluster"
        for i in range(len(spark_operator_service_accounts)):
            ns = "spark-operator" if i == 0 else namespace
            self.assert_call_matches(
                result.aws_requests[i + 1],
                spark_operator_service_accounts[i],
                cluster_name,
                ns,
                role_arn,
            )

    # Use case: Expect to return create pod identity association results for flink operator
    # Expected results: Operation is performed by client
    # to create pod identity associations with flink operator service accounts
    def test_create_role_associations_for_flink_operator(
        self,
        cli_runner,
        role_arn,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        create_pod_identity_association_response,
        flink_operator_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        result = cli_runner.run(
            [
                "emr-containers",
                "create-role-associations",
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

        assert result.aws_requests[0].service_name == "eks"
        assert result.aws_requests[0].operation_name == "DescribeCluster"
        for i in range(len(flink_operator_service_accounts)):
            self.assert_call_matches(
                result.aws_requests[i + 1],
                flink_operator_service_accounts[i],
                cluster_name,
                namespace,
                role_arn,
            )

    # Use case: Expect to return create pod identity association results for flink operator with operator namespaces
    # Expected results: Operation is performed by client
    # to create pod identity associations with flink operator service accounts in correct namespace
    def test_create_role_associations_for_flink_operator_namespace(
        self,
        cli_runner,
        role_arn,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        create_pod_identity_association_response,
        flink_operator_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        result = cli_runner.run(
            [
                "emr-containers",
                "create-role-associations",
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

        assert result.aws_requests[0].service_name == "eks"
        assert result.aws_requests[0].operation_name == "DescribeCluster"
        for i in range(len(flink_operator_service_accounts)):
            ns = "flink-operator" if i == 0 else namespace
            self.assert_call_matches(
                result.aws_requests[i + 1],
                flink_operator_service_accounts[i],
                cluster_name,
                ns,
                role_arn,
            )

    # Use case: Expect to return create pod identity association results for livy
    # Expected results: Operation is performed by client
    # to create pod identity associations with livy service accounts
    def test_create_role_associations_for_livy(
        self,
        cli_runner,
        role_arn,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        create_pod_identity_association_response,
        livy_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        result = cli_runner.run(
            [
                "emr-containers",
                "create-role-associations",
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

        assert result.aws_requests[0].service_name == "eks"
        assert result.aws_requests[0].operation_name == "DescribeCluster"
        for i in range(len(livy_service_accounts)):
            self.assert_call_matches(
                result.aws_requests[i + 1],
                livy_service_accounts[i],
                cluster_name,
                namespace,
                role_arn,
            )

    # Use case: Expect to return create pod identity association results for livy with controller namespace
    # Expected results: Operation is performed by client
    # to create pod identity associations with livy service accounts in correct namespace
    def test_create_role_associations_for_livy_namespace(
        self,
        cli_runner,
        role_arn,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        create_pod_identity_association_response,
        livy_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        result = cli_runner.run(
            [
                "emr-containers",
                "create-role-associations",
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

        assert result.aws_requests[0].service_name == "eks"
        assert result.aws_requests[0].operation_name == "DescribeCluster"
        for i in range(len(livy_service_accounts)):
            ns = "livy" if i == 0 else namespace
            self.assert_call_matches(
                result.aws_requests[i + 1],
                livy_service_accounts[i],
                cluster_name,
                ns,
                role_arn,
            )

    # Use case: Expect to return create pod identity association results for customer input service accounts
    # Expected results: Operation is performed by client
    # to create pod identity associations with customer input service accounts
    def test_create_role_associations_for_customer_service_account(
        self,
        cli_runner,
        role_arn,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        create_pod_identity_association_response,
        spark_operator_service_accounts,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        result = cli_runner.run(
            [
                "emr-containers",
                "create-role-associations",
                "--cluster-name",
                cluster_name,
                "--namespace",
                namespace,
                "--role-name",
                role_name,
                "--service-account",
                "test_sa",
            ]
        )

        assert result.aws_requests[0].service_name == "eks"
        assert result.aws_requests[0].operation_name == "DescribeCluster"
        self.assert_call_matches(
            result.aws_requests[1], "test_sa", cluster_name, namespace, role_arn
        )

    # Use case: Expect to return ResourceInUse exception and do nothing on already existed associations
    # Expected results: Association creations are skipped
    def test_create_role_associations_already_exists_for_start_job_run(
        self,
        cli_runner,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        create_pod_identity_association_already_exists_error_response,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        cli_runner.add_response(
            HTTPResponse(
                body=create_pod_identity_association_already_exists_error_response,
                status_code=409,
            )
        )
        cli_runner.add_response(
            HTTPResponse(
                body=create_pod_identity_association_already_exists_error_response,
                status_code=409,
            )
        )
        cli_runner.add_response(
            HTTPResponse(
                body=create_pod_identity_association_already_exists_error_response,
                status_code=409,
            )
        )
        result = cli_runner.run(
            [
                "emr-containers",
                "create-role-associations",
                "--cluster-name",
                cluster_name,
                "--namespace",
                namespace,
                "--role-name",
                role_name,
            ]
        )
        components = ["client", "driver", "executor"]
        expected_out = ""
        for component in components:
            expected_out += (
                f"Skipping pod identity association creation because pod identity association already exists for service "
                + f"account emr-containers-sa-spark-{component}-123456789012-16o0gwny3pand role myrole in namespace test: "
                + f"An error occurred (ResourceInUseException) when calling the "
                + f"CreatePodIdentityAssociation operation: Association already exists: a-1\n"
            )
        assert result.stderr == expected_out

    # Use case: Expect to return error exception and rollback on created associations in the same call
    # Expected results: Associations are rolled back
    def test_create_role_associations_error_rollback_for_start_job_run(
        self,
        cli_runner,
        cluster_name,
        namespace,
        role_name,
        describe_cluster_response,
        start_job_run_service_accounts,
        role_arn,
        create_pod_identity_association_response,
        create_pod_identity_association_other_error_response,
        delete_pod_identity_association_response,
    ):

        cli_runner.add_response(HTTPResponse(body=describe_cluster_response))
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(body=create_pod_identity_association_response)
        )
        cli_runner.add_response(
            HTTPResponse(
                body=create_pod_identity_association_other_error_response,
                status_code=400,
            )
        )
        for i in range(2):
            cli_runner.add_response(
                HTTPResponse(body=delete_pod_identity_association_response[i])
            )
        result = cli_runner.run(
            [
                "emr-containers",
                "create-role-associations",
                "--cluster-name",
                cluster_name,
                "--namespace",
                namespace,
                "--role-name",
                role_name,
            ]
        )

        assert result.aws_requests[0].service_name == "eks"
        assert result.aws_requests[0].operation_name == "DescribeCluster"
        for i in range(3):
            self.assert_call_matches(
                result.aws_requests[i + 1],
                start_job_run_service_accounts[i],
                cluster_name,
                namespace,
                role_arn,
            )
        for i in range(2):
            self.assert_roll_back(
                result.aws_requests[i + 4], cluster_name, "a-12345678"
            )
