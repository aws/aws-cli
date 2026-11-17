**To wait for an nodegroup running in the Amazon EKS cluster to become deleted**

The following ``wait nodegroup-deleted`` example command waits until ``ResourceNotFoundException`` is thrown when polling with `describe-nodegroup` for an nodegroup named ``my-nodegroup`` running in the Amazon EKS cluster named ``my-eks-cluster``. ::

    aws eks wait nodegroup-deleted \
        --cluster-name my-eks-cluster \
        --nodegroup-name my-nodegroup

This command produces no output.

For more information, see `Delete a managed node group from your cluster <https://docs.aws.amazon.com/eks/latest/userguide/delete-managed-node-group.html>`__ in the *Amazon EKS User Guide*.
