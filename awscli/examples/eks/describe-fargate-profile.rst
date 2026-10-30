**To describe a Fargate profile**

The following ``describe-fargate-profile`` example describes a Fargate profile. ::

    aws eks describe-fargate-profile \
        --cluster-name my-eks-cluster \
        --fargate-profile-name my-fargate-profile

Output::

    {
        "fargateProfile": {
            "fargateProfileName": "my-fargate-profile",
            "fargateProfileArn": "arn:aws:eks:us-west-2:123456789012:fargateprofile/my-eks-cluster/my-fargate-profile/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "clusterName": "my-eks-cluster",
            "createdAt": "2024-04-11T10:42:52.486000-04:00",
            "podExecutionRoleArn": "arn:aws:iam::123456789012:role/eksctl-my-eks-cluster-farga-FargatePodExecutionRole-1htfAaJdJUEO",
            "subnets": [
                "subnet-09d912bb63ef21b9a",
                "subnet-04ad87f71c6e5ab4d",
                "subnet-0e2907431c9988b72"
            ],
            "selectors": [
                {
                    "namespace": "prod*",
                    "labels": {
                        "labelname*?": "*value1"
                    }
                },
                {
                    "namespace": "*dev*",
                    "labels": {
                        "labelname*?": "*value*"
                    }
                }
            ],
            "status": "ACTIVE",
            "tags": {
                "eks-fargate-profile-key-2": "value-2",
                "eks-fargate-profile-key-1": "value-1"
            }
        }
    }

For more information, see `Define which Pods use AWS Fargate when launched <https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html>`__ in the *Amazon EKS User Guide*.
