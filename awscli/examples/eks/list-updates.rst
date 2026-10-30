**Example 1: To list the updates for a cluster**

The following ``list-updates`` example lists the current updates for a cluster named ``example`` in your default region. ::

    aws eks list-updates \
        --name example

Output::

    {
        "updateIds": [
            "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
        ]
    }

**Example 2: To list all the update IDs for an Amazon EKS Node group**

The following ``list-updates`` example lists all the update IDs for an Amazon EKS Node group. ::

    aws eks list-updates \
        --name my-eks-cluster \
        --nodegroup-name my-eks-managed-node-group

Output::

    {
        "updateIds": [
            "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
        ]
    }

**Example 3: To list all the update IDs for an Amazon EKS add-on**

The following ``list-updates`` example lists all the update IDs for an Amazon EKS Add-on. ::

    aws eks list-updates \
        --name my-eks-cluster \
        --addon-name vpc-cni

Output::

    {
        "updateIds": [
            "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"
        ]
    }

For more information, see `Update existing cluster to new Kubernetes version <https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html>`__ in the *Amazon EKS User Guide*.
