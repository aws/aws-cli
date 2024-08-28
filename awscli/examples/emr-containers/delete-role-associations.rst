**To delete role associations of an IAM Role with EMR service accounts**

This example command deletes EKS pod identity associations of a role named **example_iam_role** with EMR service accounts such that it can be removed from Amazon EMR on EKS with
**example_namespace** namespace from an EKS cluster named **example_cluster**.

EKS allows associations with non existing resources (namespace, service account), so EMR on EKS suggest to delete the associations if the namespace is deleted or the role is not in use to release the space for other associations.

* Command::

    aws emr-containers delete-role-associations \
        --cluster-name example_cluster \
        --namespace example_namespace \
        --role-name example_iam_role \
        (--type example_type) \
        (--operator-namespace operator_namespace) \
        (--service-account-name custom_service_account)

* Output::

    If the iam role has been dissociated with emr service accounts, then the output will be:
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
