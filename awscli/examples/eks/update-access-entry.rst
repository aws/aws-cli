**To update an access entry for an EKS cluster**

The following ``update-access-entry`` example updates an access entry for the EKS cluster by adding the Kubernetes group ``tester``. ::

    aws eks update-access-entry \
        --cluster-name eks-customer \
        --principal-arn arn:aws:iam::123456789012:role/Admin \
        --kubernetes-groups tester

Output::

    {
        "accessEntry": {
            "clusterName": "eks-customer",
            "principalArn": "arn:aws:iam::123456789012:role/Admin",
            "kubernetesGroups": [
                "tester"
            ],
            "accessEntryArn": "arn:aws:eks:us-west-2:123456789012:access-entry/eks-customer/role/123456789012/Admin/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "createdAt": "2025-05-24T11:02:04.432000-05:00",
            "modifiedAt": "2025-05-24T17:08:01.608000-05:00",
            "tags": {},
            "username": "arn:aws:sts::123456789012:assumed-role/Admin/{{SessionName}}",
            "type": "STANDARD"
        }
    }

For more information, see `Update access entries <https://docs.aws.amazon.com/eks/latest/userguide/updating-access-entries.html>`__ in the *Amazon EKS User Guide*.