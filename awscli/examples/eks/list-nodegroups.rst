**To list all the node groups in an Amazon EKS cluster**

The following ``list-nodegroups`` example list all the node groups in an Amazon EKS cluster. ::

    aws eks list-nodegroups \
        --cluster-name my-eks-cluster

Output::

    {
        "nodegroups": [
            "my-eks-managed-node-group",
            "my-eks-nodegroup"
        ]
    }

For more information, see `Simplify node lifecycle with managed node groups <https://docs.aws.amazon.com/eks/latest/userguide/managed-node-groups.html>`__ in the *Amazon EKS User Guide*.
