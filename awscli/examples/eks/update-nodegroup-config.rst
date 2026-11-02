**Example 1: To update a managed node group to add new labels and taint to EKS worker node for an Amazon EKS cluster**

The following ``update-nodegroup-config`` example updates a managed node group to add new labels and taint to EKS worker node for an Amazon EKS cluster. ::

    aws eks update-nodegroup-config \
        --cluster-name my-eks-cluster \
        --nodegroup-name my-eks-nodegroup \
        --labels 'addOrUpdateLabels={my-eks-nodegroup-label-1=value-1,my-eks-nodegroup-label-2=value-2}' \
        --taints 'addOrUpdateTaints=[{key=taint-key-1,value=taint-value-1,effect=NO_EXECUTE}]'

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "status": "InProgress",
            "type": "ConfigUpdate",
            "params": [
                {
                    "type": "LabelsToAdd",
                    "value": "{\"my-eks-nodegroup-label-2\":\"value-2\",\"my-eks-nodegroup-label-1\":\"value-1\"}"
                },
                {
                    "type": "TaintsToAdd",
                    "value": "[{\"effect\":\"NO_EXECUTE\",\"value\":\"taint-value-1\",\"key\":\"taint-key-1\"}]"
                }
            ],
            "createdAt": "2024-04-08T12:05:19.161000-04:00",
            "errors": []
        }
    }

For more information, see `Updating a managed node group <https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html>`__ in the *Amazon EKS User Guide*.

**Example 2: To update a managed node group to remove labels and taint for the EKS worker node for an Amazon EKS cluster**

The following ``update-nodegroup-config`` example updates a managed node group to remove labels and taint for the EKS worker node for an Amazon EKS cluster. ::

    aws eks update-nodegroup-config \
        --cluster-name my-eks-cluster \
        --nodegroup-name my-eks-nodegroup \
        --labels 'removeLabels=my-eks-nodegroup-label-1, my-eks-nodegroup-label-2' \
        --taints 'removeTaints=[{key=taint-key-1,value=taint-value-1,effect=NO_EXECUTE}]'

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "status": "InProgress",
            "type": "ConfigUpdate",
            "params": [
                {
                    "type": "LabelsToRemove",
                    "value": "[\"my-eks-nodegroup-label-1\",\"my-eks-nodegroup-label-2\"]"
                },
                {
                    "type": "TaintsToRemove",
                    "value": "[{\"effect\":\"NO_EXECUTE\",\"value\":\"taint-value-1\",\"key\":\"taint-key-1\"}]"
                }
            ],
            "createdAt": "2024-04-08T12:17:31.817000-04:00",
            "errors": []
        }
    }

For more information, see `Updating a managed node group <https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html>`__ in the *Amazon EKS User Guide*.

**Example 3: To update a managed node group to remove and add labels and taint for the EKS worker node for an Amazon EKS cluster**

The following ``update-nodegroup-config`` example updates a managed node group to remove and add labels and taint for the EKS worker node for an Amazon EKS cluster. ::

    aws eks update-nodegroup-config \
        --cluster-name my-eks-cluster \
        --nodegroup-name my-eks-nodegroup \
        --labels 'addOrUpdateLabels={my-eks-nodegroup-new-label-1=new-value-1,my-eks-nodegroup-new-label-2=new-value-2},removeLabels=my-eks-nodegroup-label-1, my-eks-nodegroup-label-2' \
        --taints 'addOrUpdateTaints=[{key=taint-new-key-1,value=taint-new-value-1,effect=PREFER_NO_SCHEDULE}],removeTaints=[{key=taint-key-1,value=taint-value-1,effect=NO_EXECUTE}]'

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
            "status": "InProgress",
            "type": "ConfigUpdate",
            "params": [
                {
                    "type": "LabelsToAdd",
                    "value": "{\"my-eks-nodegroup-new-label-1\":\"new-value-1\",\"my-eks-nodegroup-new-label-2\":\"new-value-2\"}"
                },
                {
                    "type": "LabelsToRemove",
                    "value": "[\"my-eks-nodegroup-label-1\",\"my-eks-nodegroup-label-2\"]"
                },
                {
                    "type": "TaintsToAdd",
                    "value": "[{\"effect\":\"PREFER_NO_SCHEDULE\",\"value\":\"taint-new-value-1\",\"key\":\"taint-new-key-1\"}]"
                },
                {
                    "type": "TaintsToRemove",
                    "value": "[{\"effect\":\"NO_EXECUTE\",\"value\":\"taint-value-1\",\"key\":\"taint-key-1\"}]"
                }
            ],
            "createdAt": "2024-04-08T12:30:55.486000-04:00",
            "errors": []
        }
    }

For more information, see `Updating a managed node group <https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html>`__ in the *Amazon EKS User Guide*.


**Example 4: To update a managed node group to update scaling-config and update-config for the EKS worker node for an Amazon EKS cluster**

The following ``update-nodegroup-config`` example updates a managed node group to update scaling-config and update-config for the EKS worker node for an Amazon EKS cluster. ::

    aws eks update-nodegroup-config \
        --cluster-name my-eks-cluster \
        --nodegroup-name my-eks-nodegroup \
        --scaling-config minSize=1,maxSize=5,desiredSize=2 \
        --update-config maxUnavailable=2

Output::

    {
        "update": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
            "status": "InProgress",
            "type": "ConfigUpdate",
            "params": [
                {
                    "type": "MinSize",
                    "value": "1"
                },
                {
                    "type": "MaxSize",
                    "value": "5"
                },
                {
                    "type": "DesiredSize",
                    "value": "2"
                },
                {
                    "type": "MaxUnavailable",
                    "value": "2"
                }
            ],
            "createdAt": "2024-04-08T12:35:17.036000-04:00",
            "errors": []
        }
    }

For more information, see `Updating a managed node group <https://docs.aws.amazon.com/eks/latest/userguide/update-managed-node-group.html>`__ in the *Amazon EKS User Guide*.
