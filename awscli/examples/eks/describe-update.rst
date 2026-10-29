**Example 1: To describe an update for a cluster**

The following ``describe-update`` example describes an update for a cluster named. ::

    aws eks describe-update \
        --name my-eks-cluster \
        --update-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "status": "Successful",
            "type": "EndpointAccessUpdate",
            "params": [
                {
                    "type": "EndpointPublicAccess",
                    "value": "false"
                },
                {
                    "type": "EndpointPrivateAccess",
                    "value": "true"
                }
            ],
            "createdAt": "2024-03-14T10:01:26.297000-04:00",
            "errors": []
        }
    }

For more information, see `Updating an Amazon EKS cluster Kubernetes version <https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html>`__ in the *Amazon EKS User Guide*.

**Example 2: To describe an update for a cluster**

The following ``describe-update`` example describes an update for a cluster named. ::

    aws eks describe-update \
        --name my-eks-cluster \
        --update-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "status": "Successful",
            "type": "AssociateEncryptionConfig",
            "params": [
                {
                    "type": "EncryptionConfig",
                    "value": "[{\"resources\":[\"secrets\"],\"provider\":{\"keyArn\":\"arn:aws:kms:region-code:account:key/key\"}}]"
                }
            ],
            "createdAt": "2024-03-14T11:01:26.297000-04:00",
            "errors": []
        }
    }

For more information, see `Updating an Amazon EKS cluster Kubernetes version <https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html>`__ in the *Amazon EKS User Guide*.

**Example 3: To describe an update for a cluster**

The following ``describe-update`` example describes an update for a cluster named. ::

    aws eks describe-update \
        --name my-eks-cluster \
        --update-id a1b2c3d4-5678-90ab-cdef-EXAMPLE33333

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
            "status": "Successful",
            "type": "VersionUpdate",
            "params": [
                {
                    "type": "Version",
                    "value": "1.29"
                },
                {
                    "type": "PlatformVersion",
                    "value": "eks.1"
                }
            ],
            "createdAt": "2024-03-14T12:05:26.297000-04:00",
            "errors": []
        }
    }

For more information, see `Updating an Amazon EKS cluster Kubernetes version <https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html>`__ in the *Amazon EKS User Guide*.
