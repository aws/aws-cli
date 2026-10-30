**Example 1: To wait for a cluster to become active**

This example command waits for a cluster named ``example`` to become active.

Command::

    aws eks wait cluster-active --name example

**Example 2: To wait for a cluster to be deleted**

This example command waits for a cluster named ``example`` to be deleted.

Command::

    aws eks wait cluster-deleted --name example

