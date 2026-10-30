**Example 1: To deletes the specified tags from an Amazon EKS Cluster**

The following ``untag-resource`` example deletes the specified tags from an Amazon EKS Cluster. ::

    aws eks untag-resource \
        --resource-arn arn:aws:eks:us-west-2:123456789012:cluster/my-eks-cluster \
        --tag-keys "my-eks-cluster-test-1" "my-eks-cluster-dev-1"

This command produces no output.

For more information, see `Organize Amazon EKS resources with tags <https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html>`__ in the *Amazon EKS User Guide*.

**Example 2: To deletes the specified tags from an Amazon EKS Node group**

The following ``untag-resource`` example deletes the specified tags from an Amazon EKS Node group. ::

    aws eks untag-resource \
        --resource-arn arn:aws:eks:us-west-2:123456789012:nodegroup/my-eks-cluster/my-eks-managed-node-group/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --tag-keys "my-eks-nodegroup-test-1" "my-eks-nodegroup-dev-1"

This command produces no output.

For more information, see `Organize Amazon EKS resources with tags <https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html>`__ in the *Amazon EKS User Guide*.
