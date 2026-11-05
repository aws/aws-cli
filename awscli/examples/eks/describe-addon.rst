**To describe an actively running EKS addon in your Amazon EKS cluster**

The following ``describe-addon`` example actively running EKS addon in your Amazon EKS cluster. ::

    aws eks describe-addon \
        --cluster-name my-eks-cluster \
        --addon-name vpc-cni

Output::

    {
        "addon": {
            "addonName": "vpc-cni",
            "clusterName": "my-eks-cluster",
            "status": "ACTIVE",
            "addonVersion": "v1.16.4-eksbuild.2",
            "health": {
                "issues": []
            },
            "addonArn": "arn:aws:eks:us-west-2:123456789012:addon/my-eks-cluster/vpc-cni/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "createdAt": "2024-03-14T13:18:45.417000-04:00",
            "modifiedAt": "2024-03-14T13:18:49.557000-04:00",
            "serviceAccountRoleArn": "arn:aws:iam::123456789012:role/eksctl-my-eks-cluster-addon-vpc-cni-Role1-YfakrqOC1UTm",
            "tags": {
                "eks-addon-key-3": "value-3",
                "eks-addon-key-4": "value-4"
            },
            "configurationValues": "resources:\n    limits:\n        cpu: '100m'\nenv:\n    AWS_VPC_K8S_CNI_LOGLEVEL: 'DEBUG'"
        }
    }

For more information, see `Amazon EKS add-ons <https://docs.aws.amazon.com/eks/latest/userguide/eks-add-ons.html>`__ in the *Amazon EKS User Guide*.
