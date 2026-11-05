**To delete a managed node group for an Amazon EKS cluster**

The following ``delete-nodegroup`` example deletes a managed node group for an Amazon EKS cluster. ::

    aws eks delete-nodegroup \
        --cluster-name my-eks-cluster \
        --nodegroup-name my-eks-nodegroup

Output::

    {
        "nodegroup": {
            "nodegroupName": "my-eks-nodegroup",
            "nodegroupArn": "arn:aws:eks:us-west-2:123456789012:nodegroup/my-eks-cluster/my-eks-nodegroup/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "clusterName": "my-eks-cluster",
            "version": "1.26",
            "releaseVersion": "1.26.12-20240329",
            "createdAt": "2024-04-08T13:25:15.033000-04:00",
            "modifiedAt": "2024-04-08T13:25:31.252000-04:00",
            "status": "DELETING",
            "capacityType": "SPOT",
            "scalingConfig": {
                "minSize": 1,
                "maxSize": 5,
                "desiredSize": 4
            },
            "instanceTypes": [
                "t3.large"
            ],
            "subnets": [
                "subnet-0e2907431c9988b72",
                "subnet-04ad87f71c6e5ab4d",
                "subnet-09d912bb63ef21b9a"
            ],
            "amiType": "AL2_x86_64",
            "nodeRole": "arn:aws:iam::123456789012:role/role-name",
            "labels": {
                "my-eks-nodegroup-label-2": "value-2",
                "my-eks-nodegroup-label-1": "value-1"
            },
            "taints": [
                {
                    "key": "taint-key-1",
                    "value": "taint-value-1",
                    "effect": "NO_EXECUTE"
                }
            ],
            "diskSize": 50,
            "health": {
                "issues": []
            },
            "updateConfig": {
                "maxUnavailable": 2
            },
            "tags": {
                "my-eks-nodegroup-key-1": "value-1",
                "my-eks-nodegroup-key-2": "value-2"
            }
        }
    }

For more information, see `Delete a managed node group from your cluster <https://docs.aws.amazon.com/eks/latest/userguide/delete-managed-node-group.html>`__ in the *Amazon EKS User Guide*.
