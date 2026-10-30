**Example 1: To delete an Amazon EKS add-on but preserve the add-on software on the EKS cluster**

The following ``delete-addon`` example command deletes an Amazon EKS add-on but preserve the add-on software on the EKS Cluster. ::

    aws eks delete-addon \
        --cluster-name my-eks-cluster \
        --addon-name my-eks-addon \
        --preserve

Output::

    {
        "addon": {
            "addonName": "my-eks-addon",
            "clusterName": "my-eks-cluster",
            "status": "DELETING",
            "addonVersion": "v1.9.3-eksbuild.7",
            "health": {
                "issues": []
            },
            "addonArn": "arn:aws:eks:us-west-2:123456789012:addon/my-eks-cluster/my-eks-addon/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "createdAt": "2024-03-14T11:49:09.009000-04:00",
            "modifiedAt": "2024-03-14T12:03:49.776000-04:00",
            "tags": {}
        }
    }

For more information, see `Remove an Amazon EKS add-on from a cluster <https://docs.aws.amazon.com/eks/latest/userguide/removing-an-add-on.html>`__ in the *Amazon EKS User Guide*.

**Example 2: To delete an Amazon EKS add-on and also delete the add-on software from the EKS cluster**

The following ``delete-addon`` example command deletes an Amazon EKS add-on and also delete the add-on software from the EKS Cluster. ::

    aws eks delete-addon \
        --cluster-name my-eks-cluster \
        --addon-name my-eks-addon

Output::

    {
        "addon": {
            "addonName": "my-eks-addon",
            "clusterName": "my-eks-cluster",
            "status": "DELETING",
            "addonVersion": "v1.15.1-eksbuild.1",
            "health": {
                "issues": []
            },
            "addonArn": "arn:aws:eks:us-west-2:123456789012:addon/my-eks-cluster/my-eks-addon/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "createdAt": "2024-03-14T11:45:31.983000-04:00",
            "modifiedAt": "2024-03-14T11:58:40.136000-04:00",
            "serviceAccountRoleArn": "arn:aws:iam::123456789012:role/role-name",
            "tags": {}
        }
    }

For more information, see `Remove an Amazon EKS add-on from a cluster <https://docs.aws.amazon.com/eks/latest/userguide/removing-an-add-on.html>`__ in the *Amazon EKS User Guide*.
