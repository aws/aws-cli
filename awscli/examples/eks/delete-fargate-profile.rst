**To delete an EKS Fargate profile**

The following ``delete-fargate-profile`` example creates an EKS Fargate Profile for a selector with a namespace. ::

    aws eks delete-fargate-profile \
        --cluster-name my-eks-cluster \
        --fargate-profile-name my-fargate-profile

Output::

    {
        "fargateProfile": {
            "fargateProfileName": "my-fargate-profile",
            "fargateProfileArn": "arn:aws:eks:us-west-2:123456789012:fargateprofile/my-eks-cluster/my-fargate-profile/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "clusterName": "my-eks-cluster",
            "createdAt": "2024-03-19T11:48:39.975000-04:00",
            "podExecutionRoleArn": "arn:aws:iam::123456789012:role/role-name",
            "subnets": [
                "subnet-09d912bb63ef21b9a",
                "subnet-04ad87f71c6e5ab4d",
                "subnet-0e2907431c9988b72"
            ],
            "selectors": [
                {
                    "namespace": "default",
                    "labels": {
                        "foo": "bar"
                    }
                }
            ],
            "status": "DELETING",
            "tags": {}
        }
    }

For more information, see `AWS Fargate profile - Deleting a Fargate <https://docs.aws.amazon.com/eks/latest/userguide/delete-fargate-profile.html>`__ in the *Amazon EKS User Guide*.
