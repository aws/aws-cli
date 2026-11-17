**To wait for an fargate-profile running in the Amazon EKS cluster to become deleted**

The following ``wait fargate-profile-deleted`` example command waits until ``ResourceNotFoundException`` is thrown when polling with `describe-fargate-profile` for an fargate-profile named ``my-fargate-profile`` running in the Amazon EKS cluster named ``my-eks-cluster``. ::

    aws eks wait fargate-profile-deleted \
        --cluster-name my-eks-cluster \
        --fargate-profile-name my-fargate-profile

This command produces no output.

For more information, see `Delete a Fargate profile <https://docs.aws.amazon.com/eks/latest/userguide/delete-fargate-profile.html>`__ in the *Amazon EKS User Guide*.
