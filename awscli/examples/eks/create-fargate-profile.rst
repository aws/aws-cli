**Example 1: To create an EKS Fargate profile for a selector with a namespace**

The following ``create-fargate-profile`` example creates an EKS Fargate Profile for a selector with a namespace. ::

    aws eks create-fargate-profile \
        --cluster-name my-eks-cluster \
        --pod-execution-role-arn arn:aws:iam::123456789012:role/role-name \
        --fargate-profile-name my-fargate-profile \
        --selectors '[{"namespace": "default"}]'
    
Output::

    {
        "fargateProfile": {
            "fargateProfileName": "my-fargate-profile",
            "fargateProfileArn": "arn:aws:eks:us-west-2:123456789012:fargateprofile/my-eks-cluster/my-fargate-profile/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "clusterName": "my-eks-cluster",
            "createdAt": "2024-03-19T12:38:47.368000-04:00",
            "podExecutionRoleArn": "arn:aws:iam::123456789012:role/role-name",
            "subnets": [
                "subnet-09d912bb63ef21b9a",
                "subnet-04ad87f71c6e5ab4d",
                "subnet-0e2907431c9988b72"
            ],
            "selectors": [
                {
                    "namespace": "default"
                }
            ],
            "status": "CREATING",
            "tags": {}
        }
    }

For more information, see `AWS Fargate profile - Creating a Fargate profile <https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html#create-fargate-profile>`__ in the *Amazon EKS User Guide*.

**Example 2: To create an EKS Fargate profile for a selector with a namespace and labels**

The following ``create-fargate-profile`` example creates an EKS Fargate Profile for a selector with a namespace and labels. ::

    aws eks create-fargate-profile \
        --cluster-name my-eks-cluster \
        --pod-execution-role-arn arn:aws:iam::123456789012:role/role-name \
        --fargate-profile-name my-fargate-profile \
        --selectors '[{"namespace": "default", "labels": {"labelname1": "labelvalue1"}}]'

Output::

    {
        "fargateProfile": {
            "fargateProfileName": "my-fargate-profile",
            "fargateProfileArn": "arn:aws:eks:us-west-2:123456789012:fargateprofile/my-eks-cluster/my-fargate-profile/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "clusterName": "my-eks-cluster",
            "createdAt": "2024-03-19T12:33:48.125000-04:00",
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
                        "labelname1": "labelvalue1"
                    }
                }
            ],
            "status": "CREATING",
            "tags": {}
        }
    }

For more information, see `AWS Fargate profile - Creating a Fargate profile <https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html#create-fargate-profile>`__ in the *Amazon EKS User Guide*.

**Example 3: To create an EKS Fargate profile for a selector with a namespace and labels, along with IDs of subnets to launch a Pod into**

The following ``create-fargate-profile`` example create EKS Fargate Profile for a selector with a namespace and labels, along with IDs of subnets to launch a Pod into. ::

    aws eks create-fargate-profile \
        --cluster-name my-eks-cluster \
        --pod-execution-role-arn arn:aws:iam::123456789012:role/role-name \
        --fargate-profile-name my-fargate-profile \
        --selectors '[{"namespace": "default", "labels": {"labelname1": "labelvalue1"}}]' \
        --subnets '["subnet-09d912bb63ef21b9a", "subnet-04ad87f71c6e5ab4d", "subnet-0e2907431c9988b72"]'

Output::

    {
        "fargateProfile": {
            "fargateProfileName": "my-fargate-profile",
            "fargateProfileArn": "arn:aws:eks:us-west-2:123456789012:fargateprofile/my-eks-cluster/my-fargate-profile/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
            "clusterName": "my-eks-cluster",
            "createdAt": "2024-03-19T12:35:58.640000-04:00",
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
                        "labelname1": "labelvalue1"
                    }
                }
            ],
            "status": "CREATING",
            "tags": {}
        }
    }

For more information, see `AWS Fargate profile - Creating a Fargate profile <https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html#create-fargate-profile>`__ in the *Amazon EKS User Guide*.

**Example 4: To create an EKS Fargate profile for a selector with multiple namespaces and labels, along with IDs of subnets to launch a Pod into**

The following ``create-fargate-profile`` example creates an EKS Fargate Profile for a selector with multiple namespace and labels, along with IDs of subnets to launch a Pod into. ::

    aws eks create-fargate-profile \
        --cluster-name my-eks-cluster \
        --pod-execution-role-arn arn:aws:iam::123456789012:role/role-name \
        --fargate-profile-name my-fargate-profile \
        --selectors '[{"namespace": "default1", "labels": {"labelname1": "labelvalue1", "labelname2": "labelvalue2"}}, {"namespace": "default2", "labels": {"labelname1": "labelvalue1", "labelname2": "labelvalue2"}}]' \
        --subnets '["subnet-09d912bb63ef21b9a", "subnet-04ad87f71c6e5ab4d", "subnet-0e2907431c9988b72"]' \
        --tags '{"eks-fargate-profile-key-1": "value-1" , "eks-fargate-profile-key-2": "value-2"}'

Output::

    {
        "fargateProfile": {
            "fargateProfileName": "my-fargate-profile",
            "fargateProfileArn": "arn:aws:eks:us-west-2:123456789012:fargateprofile/my-eks-cluster/my-fargate-profile/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
            "clusterName": "my-eks-cluster",
            "createdAt": "2024-03-19T12:15:55.271000-04:00",
            "podExecutionRoleArn": "arn:aws:iam::123456789012:role/role-name",
            "subnets": [
                "subnet-09d912bb63ef21b9a",
                "subnet-04ad87f71c6e5ab4d",
                "subnet-0e2907431c9988b72"
            ],
            "selectors": [
                {
                    "namespace": "default1",
                    "labels": {
                        "labelname2": "labelvalue2",
                        "labelname1": "labelvalue1"
                    }
                },
                {
                    "namespace": "default2",
                    "labels": {
                        "labelname2": "labelvalue2",
                        "labelname1": "labelvalue1"
                    }
                }
            ],
            "status": "CREATING",
            "tags": {
                "eks-fargate-profile-key-2": "value-2",
                "eks-fargate-profile-key-1": "value-1"
            }
        }
    }

For more information, see `AWS Fargate profile - Creating a Fargate profile <https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html#create-fargate-profile>`__ in the *Amazon EKS User Guide*.

**Example 5: To create an EKS Fargate profile with a wildcard selector for namespaces and labels, along with IDs of subnets to launch a Pod into**

The following ``create-fargate-profile`` example creates an EKS Fargate Profile for a selector with multiple namespace and labels, along with IDs of subnets to launch a Pod into. ::

    aws eks create-fargate-profile \
        --cluster-name my-eks-cluster \
        --pod-execution-role-arn arn:aws:iam::123456789012:role/role-name \
        --fargate-profile-name my-fargate-profile \
        --selectors '[{"namespace": "prod*", "labels": {"labelname*?": "*value1"}}, {"namespace": "*dev*", "labels": {"labelname*?": "*value*"}}]' \
        --subnets '["subnet-09d912bb63ef21b9a", "subnet-04ad87f71c6e5ab4d", "subnet-0e2907431c9988b72"]' \
        --tags '{"eks-fargate-profile-key-1": "value-1" , "eks-fargate-profile-key-2": "value-2"}'

Output::

    {
        "fargateProfile": {
            "fargateProfileName": "my-fargate-profile",
            "fargateProfileArn": "arn:aws:eks:us-west-2:123456789012:fargateprofile/my-eks-cluster/my-fargate-profile/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
            "clusterName": "my-eks-cluster",
            "createdAt": "2024-03-19T13:05:20.550000-04:00",
            "podExecutionRoleArn": "arn:aws:iam::123456789012:role/role-name",
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
            "status": "CREATING",
            "tags": {
                "eks-fargate-profile-key-2": "value-2",
                "eks-fargate-profile-key-1": "value-1"
            }
        }
    }

For more information, see `AWS Fargate profile - Creating a Fargate profile <https://docs.aws.amazon.com/eks/latest/userguide/fargate-profile.html#create-fargate-profile>`__ in the *Amazon EKS User Guide*.
