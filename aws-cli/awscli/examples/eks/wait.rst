**Example 1: To wait for a cluster to become active**

The following ``wait`` example uses the ``cluster-active`` waiter to pause and resume running only after a cluster named ``example`` becomes active. ::

    aws eks wait cluster-active \
        --name example

This command produces no output.

For more information, see `Create an Amazon EKS cluster <https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html>`__ in the *Amazon EKS User Guide*.

**Example 2: To wait for a cluster to be deleted**

The following ``wait`` example uses the ``cluster-deleted`` waiter to pause and resume running only after a cluster named ``example`` is deleted. ::

    aws eks wait cluster-deleted \
        --name example

This command produces no output.

For more information, see `Delete a cluster <https://docs.aws.amazon.com/eks/latest/userguide/delete-cluster.html>`__ in the *Amazon EKS User Guide*.
