**To wait for an add-on running in the Amazon EKS cluster to become ACTIVE**

The following ``wait addon-active`` example command waits for an add-on named ``aws-efs-csi-driver`` running in the Amazon EKS cluster named ``my-eks-cluster`` to become ``ACTIVE``. ::

    aws eks wait addon-active \
        --cluster-name my-eks-cluster \
        --addon-name aws-efs-csi-driver

This command produces no output.

For more information, see `Create an Amazon EKS add-on <https://docs.aws.amazon.com/eks/latest/userguide/creating-an-add-on.html>`__ in the *Amazon EKS User Guide*.
