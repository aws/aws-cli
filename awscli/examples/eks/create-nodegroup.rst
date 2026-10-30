**Example 1: To create a managed node group for an Amazon EKS cluster**

The following ``create-nodegroup`` example creates a managed node group for an Amazon EKS cluster. ::

    aws eks create-nodegroup \
        --cluster-name my-eks-cluster \
        --nodegroup-name my-eks-nodegroup \
        --node-role arn:aws:iam::123456789012:role/role-name \
        --subnets "subnet-0e2907431c9988b72" "subnet-04ad87f71c6e5ab4d" "subnet-09d912bb63ef21b9a" \
        --scaling-config minSize=1,maxSize=3,desiredSize=1

Output::

    {
        "nodegroup": {
            "nodegroupName": "my-eks-nodegroup",
            "nodegroupArn": "arn:aws:eks:us-west-2:123456789012:nodegroup/my-eks-cluster/my-eks-nodegroup/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "clusterName": "my-eks-cluster",
            "version": "1.26",
            "releaseVersion": "1.26.12-20240329",
            "createdAt": "2024-04-04T13:19:32.260000-04:00",
            "modifiedAt": "2024-04-04T13:19:32.260000-04:00",
            "status": "CREATING",
            "capacityType": "ON_DEMAND",
            "scalingConfig": {
                "minSize": 1,
                "maxSize": 3,
                "desiredSize": 1
            },
            "instanceTypes": [
                "t3.medium"
            ],
            "subnets": [
                "subnet-0e2907431c9988b72, subnet-04ad87f71c6e5ab4d, subnet-09d912bb63ef21b9a"
            ],
            "amiType": "AL2_x86_64",
            "nodeRole": "arn:aws:iam::123456789012:role/role-name",
            "diskSize": 20,
            "health": {
                "issues": []
            },
            "updateConfig": {
                "maxUnavailable": 1
            },
            "tags": {}
        }
    }

For more information, see `Creating a managed node group <https://docs.aws.amazon.com/eks/latest/userguide/create-managed-node-group.html>`__ in the *Amazon EKS User Guide*.

**Example 2: To create a managed node group for an Amazon EKS cluster with custom instance-types and disk-size**

The following ``create-nodegroup`` example creates a managed node group for an Amazon EKS cluster with custom instance-types and disk-size. ::

    aws eks create-nodegroup \
        --cluster-name my-eks-cluster \
        --nodegroup-name my-eks-nodegroup \
        --node-role arn:aws:iam::123456789012:role/role-name \
        --subnets "subnet-0e2907431c9988b72" "subnet-04ad87f71c6e5ab4d" "subnet-09d912bb63ef21b9a" \
        --scaling-config minSize=1,maxSize=3,desiredSize=1 \
        --capacity-type ON_DEMAND \
        --instance-types 'm5.large' \
        --disk-size 50

Output::

    {
        "nodegroup": {
            "nodegroupName": "my-eks-nodegroup",
            "nodegroupArn": "arn:aws:eks:us-west-2:123456789012:nodegroup/my-eks-cluster/my-eks-nodegroup/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "clusterName": "my-eks-cluster",
            "version": "1.26",
            "releaseVersion": "1.26.12-20240329",
            "createdAt": "2024-04-04T13:46:07.595000-04:00",
            "modifiedAt": "2024-04-04T13:46:07.595000-04:00",
            "status": "CREATING",
            "capacityType": "ON_DEMAND",
            "scalingConfig": {
                "minSize": 1,
                "maxSize": 3,
                "desiredSize": 1
            },
            "instanceTypes": [
                "m5.large"
            ],
            "subnets": [
                "subnet-0e2907431c9988b72",
                "subnet-04ad87f71c6e5ab4d",
                "subnet-09d912bb63ef21b9a"
            ],
            "amiType": "AL2_x86_64",
            "nodeRole": "arn:aws:iam::123456789012:role/role-name",
            "diskSize": 50,
            "health": {
                "issues": []
            },
            "updateConfig": {
                "maxUnavailable": 1
            },
            "tags": {}
        }
    }

For more information, see `Creating a managed node group <https://docs.aws.amazon.com/eks/latest/userguide/create-managed-node-group.html>`__ in the *Amazon EKS User Guide*.

**Example 3: To create a managed node group for an Amazon EKS cluster with custom instance-types, disk-size, ami-type, capacity-type, update-config, labels, taints and tags**

The following ``create-nodegroup`` example creates a managed node group for an Amazon EKS cluster with custom instance-types, disk-size, ami-type, capacity-type, update-config, labels, taints and tags. ::

    aws eks create-nodegroup  \
        --cluster-name my-eks-cluster \
        --nodegroup-name my-eks-nodegroup \
        --node-role arn:aws:iam::123456789012:role/role-name \
        --subnets "subnet-0e2907431c9988b72" "subnet-04ad87f71c6e5ab4d" "subnet-09d912bb63ef21b9a" \
        --scaling-config minSize=1,maxSize=5,desiredSize=4 \
        --instance-types 't3.large' \
        --disk-size 50 \
        --ami-type AL2_x86_64 \
        --capacity-type SPOT \
        --update-config maxUnavailable=2 \
        --labels '{"my-eks-nodegroup-label-1": "value-1" , "my-eks-nodegroup-label-2": "value-2"}' \
        --taints '{"key": "taint-key-1" , "value": "taint-value-1", "effect": "NO_EXECUTE"}' \
        --tags '{"my-eks-nodegroup-key-1": "value-1" , "my-eks-nodegroup-key-2": "value-2"}'

Output::

    {
        "nodegroup": {
            "nodegroupName": "my-eks-nodegroup",
            "nodegroupArn": "arn:aws:eks:us-west-2:123456789012:nodegroup/my-eks-cluster/my-eks-nodegroup/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
            "clusterName": "my-eks-cluster",
            "version": "1.26",
            "releaseVersion": "1.26.12-20240329",
            "createdAt": "2024-04-04T14:05:07.940000-04:00",
            "modifiedAt": "2024-04-04T14:05:07.940000-04:00",
            "status": "CREATING",
            "capacityType": "SPOT",
            "scalingConfig": {
                "minSize": 1,
                "maxSize": 5,
                "desiredSize": 4
            },
            "instanceTypes": [
                "t3.large"
            ],
            "subnets": [
                "subnet-0e2907431c9988b72",
                "subnet-04ad87f71c6e5ab4d",
                "subnet-09d912bb63ef21b9a"
            ],
            "amiType": "AL2_x86_64",
            "nodeRole": "arn:aws:iam::123456789012:role/role-name",
            "labels": {
                "my-eks-nodegroup-label-2": "value-2",
                "my-eks-nodegroup-label-1": "value-1"
            },
            "taints": [
                {
                    "key": "taint-key-1",
                    "value": "taint-value-1",
                    "effect": "NO_EXECUTE"
                }
            ],
            "diskSize": 50,
            "health": {
                "issues": []
            },
            "updateConfig": {
                "maxUnavailable": 2
            },
            "tags": {
                "my-eks-nodegroup-key-1": "value-1",
                "my-eks-nodegroup-key-2": "value-2"
            }
        }
    }

For more information, see `Creating a managed node group <https://docs.aws.amazon.com/eks/latest/userguide/create-managed-node-group.html>`__ in the *Amazon EKS User Guide*.