**Example 1: To wait for a cluster to become active**

The following ``wait`` example uses the ``cluster-active`` waiter to pause and resume running only after a cluster named ``example`` becomes active. This command produces no output. ::

    aws eks wait cluster-active \
        --name example

**Example 2: To wait for a cluster to be deleted**

The following ``wait`` example uses the ``cluster-deleted`` waiter to pause and resume running only after a cluster named ``example`` is deleted. This command produces no output. ::

    aws eks wait cluster-deleted \
        --name example

