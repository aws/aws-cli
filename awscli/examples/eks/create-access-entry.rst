**Example 1: To create the access entry for EKS cluster**

The following ``create-access-entry`` example creates an access entry that allows an IAM principal to access the EKS cluster. ::

    aws eks create-access-entry \
        --cluster-name eks-customer \
        --principal-arn arn:aws:iam::123456789012:user/eks-user

Output::

    {
        "accessEntry": {
            "clusterName": "eks-customer",
            "principalArn": "arn:aws:iam::123456789012:user/eks-user",
            "kubernetesGroups": [],
            "accessEntryArn": "arn:aws:eks:us-west-2:123456789012:access-entry/eks-customer/user/123456789012/eks-user/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "createdAt": "2025-04-14T22:45:48.097000-05:00",
            "modifiedAt": "2025-04-14T22:45:48.097000-05:00",
            "tags": {},
            "username": "arn:aws:iam::123456789012:user/eks-user",
            "type": "STANDARD"
        }
    }

For more information, see `Create access entries <https://docs.aws.amazon.com/eks/latest/userguide/creating-access-entries.html>`__ in the *Amazon EKS User Guide*.

**Example 2: To create the access entry for EKS cluster by specifying the type of access entry**

The following ``create-access-entry`` example creates an access entry of type ``EC2_LINUX`` in the EKS cluster. By default, a type ``STANDARD`` access entry is created. Apart from the default, if we specify any other access entry types, an IAM role ARN needs to be passed in the CLI. ::

    aws eks create-access-entry \
        --cluster-name eks-customer \
        --principal-arn arn:aws:iam::123456789012:role/admin-test-ip \
        --type EC2_LINUX

Output::

    {
        "accessEntry": {
            "clusterName": "eks-customer",
            "principalArn": "arn:aws:iam::123456789012:role/admin-test-ip",
            "kubernetesGroups": [
                "system:nodes"
            ],
            "accessEntryArn": "arn:aws:eks:us-west-2:123456789012:access-entry/eks-customer/role/123456789012/admin-test-ip/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "createdAt": "2025-05-06T19:42:45.453000-05:00",
            "modifiedAt": "2025-05-06T19:42:45.453000-05:00",
            "tags": {},
            "username": "system:node:{{EC2PrivateDNSName}}",
            "type": "EC2_LINUX"
        }
    }

For more information, see `Create access entries <https://docs.aws.amazon.com/eks/latest/userguide/creating-access-entries.html>`__ in the *Amazon EKS User Guide*.
