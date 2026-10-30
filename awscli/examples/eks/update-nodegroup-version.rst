**Example 1: To update the Kubernetes version or AMI version of an Amazon EKS managed node group to the latest available version**

The following ``update-nodegroup-version`` example updates the Kubernetes version or AMI version of an Amazon EKS managed node group to the latest available version for your Kubernetes cluster. ::

    aws eks update-nodegroup-version \
        --cluster-name my-eks-cluster \
        --nodegroup-name my-eks-nodegroup \
        --no-force

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "status": "InProgress",
            "type": "VersionUpdate",
            "params": [
                {
                    "type": "Version",
                    "value": "1.26"
                },
                {
                    "type": "ReleaseVersion",
                    "value": "1.26.12-20240329"
                }
            ],
            "createdAt": "2024-04-08T13:16:00.724000-04:00",
            "errors": []
        }
    }

For more information, see `Updating a managed node group <https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html>`__ in the *Amazon EKS User Guide*.

**Example 2: To update the Kubernetes version or AMI version of an Amazon EKS managed node group to a specified AMI release version**

The following ``update-nodegroup-version`` example updates the Kubernetes version or AMI version of an Amazon EKS managed node group to the specified AMI release version. ::

    aws eks update-nodegroup-version \
        --cluster-name my-eks-cluster \
        --nodegroup-name my-eks-nodegroup \
        --kubernetes-version '1.26' \
        --release-version '1.26.12-20240307' \
        --no-force

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "status": "InProgress",
            "type": "VersionUpdate",
            "params": [
                {
                    "type": "Version",
                    "value": "1.26"
                },
                {
                    "type": "ReleaseVersion",
                    "value": "1.26.12-20240307"
                }
            ],
            "createdAt": "2024-04-08T13:13:58.595000-04:00",
            "errors": []
        }
    }

For more information, see `Updating a managed node group - <https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html>``__ in the *Amazon EKS User Guide*.
