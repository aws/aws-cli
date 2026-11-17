**To delete role associations of an IAM Role with EMR service accounts**

The following ``delete-role-associations`` example deletes EKS pod identity associations of a role named **example_iam_role** with EMR service accounts such that it can be removed from Amazon EMR on EKS with
**example_namespace** namespace from an EKS cluster named **example_cluster**.

EKS allows associations with non existing resources (namespace, service account), so EMR on EKS suggest to delete the associations if the namespace is deleted or the role is not in use to release the space for other associations. ::

    aws emr-containers delete-role-associations \
        --cluster-name example_cluster \
        --namespace example_namespace \
        --role-name example_iam_role

Output::

    [
        {
            "clusterName": "example_cluster",
            "namespace": "example_namespace",
            "serviceAccount": "emr-spark-client-service-account-example",
            "roleArn": "arn:aws:iam::123456789012:role/example_iam_role",
            "associationArn": "arn:aws:eks:us-west-2:123456789012:podidentityassociation/example_cluster/a-bgyr1umgdmrk1kdtq",
            "associationId": "a-bgyr1umgdmrk1kdtq",
            "tags": {},
            "createdAt": "2022-11-15T10:49:00+00:00",
            "modifiedAt": "2022-11-15T10:49:00+00:00"
        },
        {
            "clusterName": "example_cluster",
            "namespace": "example_namespace",
            "serviceAccount": "emr-spark-driver-service-account-example",
            "roleArn": "arn:aws:iam::123456789012:role/example_iam_role",
            "associationArn": "arn:aws:eks:us-west-2:123456789012:podidentityassociation/example_cluster/b-bgyr1umgdmrk1kdtq",
            "associationId": "b-bgyr1umgdmrk1kdtq",
            "tags": {},
            "createdAt": "2022-11-15T10:49:00+00:00",
            "modifiedAt": "2022-11-15T10:49:00+00:00"
        },
        {
            "clusterName": "example_cluster",
            "namespace": "example_namespace",
            "serviceAccount": "emr-spark-executor-service-account-example",
            "roleArn": "arn:aws:iam::123456789012:role/example_iam_role",
            "associationArn": "arn:aws:eks:us-west-2:123456789012:podidentityassociation/example_cluster/c-bgyr1umgdmrk1kdtq",
            "associationId": "c-bgyr1umgdmrk1kdtq",
            "tags": {},
            "createdAt": "2022-11-15T10:49:00+00:00",
            "modifiedAt": "2022-11-15T10:49:00+00:00"
        }
    ]

For more information, see `Option 1: Enable EKS Pod Identity on the EKS Cluster <https://docs.aws.amazon.com/emr/latest/EMR-on-EKS-DevelopmentGuide/setting-up-enable-IAM.html>`__ in the *Amazon EMR on EKS Development Guide*.
