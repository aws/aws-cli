**To create role associations of an IAM Role with EMR service accounts to be used with Amazon EMR on EKS**

This example command creates EKS pod identity associations of a role named **example_iam_role** with EMR service accounts such that it can be used with Amazon EMR on EKS with
**example_namespace** namespace from an EKS cluster named **example_cluster**.

* Command::

    aws emr-containers create-role-associations \
        --cluster-name example_cluster \
        --namespace example_namespace \
        --role-name example_iam_role \
        (--type example_type) \
        (--operator-namespace operator_namespace) \
        (--service-account-name custom_service_account)

* Output::

    If the iam role has already been associated with emr service accounts for pod identity, then the output will be:
    An error occurred (ResourceInUseException) when calling the CreatePodIdentityAssociation operation: Association already exists: <association-id>

    If the iam role has not been associated with emr service accounts yet, then the output will be:
    [
        {
            "clusterName": "example_cluster",
            "namespace": "example_namespace",
            "serviceAccount": "emr-spark-client-service-account-example",
            "roleArn": "example_iam_role",
            "associationArn": "example_association_arn",
            "associationId": "example_association_id",
            "tags": {},
            "createdAt": "example_created_at",
            "modifiedAt": "example_modified_at"
        },
        {
            "clusterName": "example_cluster",
            "namespace": "example_namespace",
            "serviceAccount": "emr-spark-driver-service-account-example",
            "roleArn": "example_iam_role",
            "associationArn": "example_association_arn",
            "associationId": "example_association_id",
            "tags": {},
            "createdAt": "example_created_at",
            "modifiedAt": "example_modified_at"
        },
        {
            "clusterName": "example_cluster",
            "namespace": "example_namespace",
            "serviceAccount": "emr-spark-executor-service-account-example",
            "roleArn": "example_iam_role",
            "associationArn": "example_association_arn",
            "associationId": "example_association_id",
            "tags": {},
            "createdAt": "example_created_at",
            "modifiedAt": "example_modified_at"
        }
    ]   
