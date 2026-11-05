**Example 1: To update an Amazon EKS add-on with service account role ARN**

The following ``update-addon`` example command updates an Amazon EKS add-on with service account role ARN. ::

    aws eks update-addon \
        --cluster-name my-eks-cluster \
        --addon-name vpc-cni \
        --service-account-role-arn arn:aws:iam::123456789012:role/eksctl-my-eks-cluster-addon-vpc-cni-Role1-YfakrqOC1UTm

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "status": "InProgress",
            "type": "AddonUpdate",
            "params": [
                {
                    "type": "ServiceAccountRoleArn",
                    "value": "arn:aws:iam::123456789012:role/eksctl-my-eks-cluster-addon-vpc-cni-Role1-YfakrqOC1UTm"
                }
            ],
            "createdAt": "2024-04-12T16:04:55.614000-04:00",
            "errors": []
        }
    }

For more information, see `Managing Amazon EKS add-ons - Updating an add-on <https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html>`__ in the *Amazon EKS User Guide*.

**Example 2: To update an Amazon EKS add-on with specific add-on version**

The following ``update-addon`` example command updates an Amazon EKS add-on with specific add-on version. ::

    aws eks update-addon \
        --cluster-name my-eks-cluster \
        --addon-name vpc-cni \
        --service-account-role-arn arn:aws:iam::123456789012:role/eksctl-my-eks-cluster-addon-vpc-cni-Role1-YfakrqOC1UTm \
        --addon-version v1.16.4-eksbuild.2

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "status": "InProgress",
            "type": "AddonUpdate",
            "params": [
                {
                    "type": "AddonVersion",
                    "value": "v1.16.4-eksbuild.2"
                },
                {
                    "type": "ServiceAccountRoleArn",
                    "value": "arn:aws:iam::123456789012:role/eksctl-my-eks-cluster-addon-vpc-cni-Role1-YfakrqOC1UTm"
                }
            ],
            "createdAt": "2024-04-12T16:07:16.550000-04:00",
            "errors": []
        }
    }

For more information, see `Managing Amazon EKS add-ons - Updating an add-on <https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html>`__ in the *Amazon EKS User Guide*.

**Example 3: To update an Amazon EKS add-on with custom configuration values and resolve conflicts details**

The following ``update-addon`` example command updates an Amazon EKS add-on with custom configuration values and resolve conflicts details. ::

    aws eks update-addon \
        --cluster-name my-eks-cluster \
        --addon-name vpc-cni \
        --service-account-role-arn arn:aws:iam::123456789012:role/eksctl-my-eks-cluster-addon-vpc-cni-Role1-YfakrqOC1UTm \
        --addon-version v1.16.4-eksbuild.2 \
        --configuration-values '{"resources": {"limits":{"cpu":"100m"}, "requests":{"cpu":"50m"}}}' \
        --resolve-conflicts PRESERVE

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
            "status": "InProgress",
            "type": "AddonUpdate",
            "params": [
                {
                    "type": "AddonVersion",
                    "value": "v1.16.4-eksbuild.2"
                },
                {
                    "type": "ServiceAccountRoleArn",
                    "value": "arn:aws:iam::123456789012:role/eksctl-my-eks-cluster-addon-vpc-cni-Role1-YfakrqOC1UTm"
                },
                {
                    "type": "ResolveConflicts",
                    "value": "PRESERVE"
                },
                {
                    "type": "ConfigurationValues",
                    "value": "{\"resources\": {\"limits\":{\"cpu\":\"100m\"}, \"requests\":{\"cpu\":\"50m\"}}}"
                }
            ],
            "createdAt": "2024-04-12T16:16:27.363000-04:00",
            "errors": []
        }
    }

For more information, see `Managing Amazon EKS add-ons - Updating an add-on <https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html>`__ in the *Amazon EKS User Guide*.

**Example 4: To update an Amazon EKS add-on with custom JSON configuration values file**

The following ``update-addon`` example command updates an Amazon EKS add-on with custom JSON configuration values and resolve conflicts details. ::

    aws eks update-addon \
        --cluster-name my-eks-cluster \
        --addon-name vpc-cni \
        --service-account-role-arn arn:aws:iam::123456789012:role/eksctl-my-eks-cluster-addon-vpc-cni-Role1-YfakrqOC1UTm \
        --addon-version v1.17.1-eksbuild.1 \
        --configuration-values 'file://configuration-values.json' \
        --resolve-conflicts PRESERVE

Contents of ``configuration-values.json``::

    {
        "resources": {
            "limits": {
                "cpu": "100m"
            },
            "requests": {
                "cpu": "50m"
            }
        },
        "env": {
            "AWS_VPC_K8S_CNI_LOGLEVEL": "ERROR"
        }
    }

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
            "status": "InProgress",
            "type": "AddonUpdate",
            "params": [
                {
                    "type": "AddonVersion",
                    "value": "v1.17.1-eksbuild.1"
                },
                {
                    "type": "ServiceAccountRoleArn",
                    "value": "arn:aws:iam::123456789012:role/eksctl-my-eks-cluster-addon-vpc-cni-Role1-YfakrqOC1UTm"
                },
                {
                    "type": "ResolveConflicts",
                    "value": "PRESERVE"
                },
                {
                    "type": "ConfigurationValues",
                    "value": "{\n    \"resources\": {\n        \"limits\": {\n            \"cpu\": \"100m\"\n        },\n        \"requests\": {\n            \"cpu\": \"50m\"\n        }\n    },\n    \"env\": {\n        \"AWS_VPC_K8S_CNI_LOGLEVEL\": \"ERROR\"\n    }\n}"
                }
            ],
            "createdAt": "2024-04-12T16:22:55.519000-04:00",
            "errors": []
        }
    }

For more information, see `Managing Amazon EKS add-ons - Updating an add-on <https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html>`__ in the *Amazon EKS User Guide*.

**Example 5: To update an Amazon EKS add-on with custom YAML configuration values file**

The following ``update-addon`` example command updates an Amazon EKS add-on with custom YAML configuration values and resolve conflicts details. ::

    aws eks update-addon \
        --cluster-name my-eks-cluster \
        --addon-name vpc-cni \
        --service-account-role-arn arn:aws:iam::123456789012:role/eksctl-my-eks-cluster-addon-vpc-cni-Role1-YfakrqOC1UTm \
        --addon-version v1.18.0-eksbuild.1 \
        --configuration-values 'file://configuration-values.yaml' \
        --resolve-conflicts PRESERVE

Contents of ``configuration-values.yaml``::

    resources:
        limits:
            cpu: '100m'
        requests:
            cpu: '50m'
    env:
        AWS_VPC_K8S_CNI_LOGLEVEL: 'DEBUG'

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
            "status": "InProgress",
            "type": "AddonUpdate",
            "params": [
                {
                    "type": "AddonVersion",
                    "value": "v1.18.0-eksbuild.1"
                },
                {
                    "type": "ServiceAccountRoleArn",
                    "value": "arn:aws:iam::123456789012:role/eksctl-my-eks-cluster-addon-vpc-cni-Role1-YfakrqOC1UTm"
                },
                {
                    "type": "ResolveConflicts",
                    "value": "PRESERVE"
                },
                {
                    "type": "ConfigurationValues",
                    "value": "resources:\n    limits:\n        cpu: '100m'\n    requests:\n        cpu: '50m'\nenv:\n    AWS_VPC_K8S_CNI_LOGLEVEL: 'DEBUG'"
                }
            ],
            "createdAt": "2024-04-12T16:25:07.212000-04:00",
            "errors": []
        }
    }

For more information, see `Managing Amazon EKS add-ons - Updating an add-on <https://docs.aws.amazon.com/eks/latest/userguide/updating-an-add-on.html>`__ in the *Amazon EKS User Guide*.
