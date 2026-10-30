**To updates an Amazon EKS cluster named `my-eks-cluster` to the specified Kubernetes version**

The following ``update-cluster-version`` example updates an Amazon EKS cluster to the specified Kubernetes version. ::

    aws eks update-cluster-version \
        --name my-eks-cluster \
        --kubernetes-version 1.27

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "status": "InProgress",
            "type": "VersionUpdate",
            "params": [
                {
                    "type": "Version",
                    "value": "1.27"
                },
                {
                    "type": "PlatformVersion",
                    "value": "eks.16"
                }
            ],
            "createdAt": "2024-04-12T16:56:01.082000-04:00",
            "errors": []
        }
    }

For more information, see `Updating an Amazon EKS cluster Kubernetes version <https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html>`__ in the *Amazon EKS User Guide*.
