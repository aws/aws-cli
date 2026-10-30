**Example 1: To delete a cluster with no final cluster snapshot**

This example deletes a cluster, forcing data deletion so no final cluster snapshot
is created.

Command::

    aws redshift delete-cluster --cluster-identifier mycluster --skip-final-cluster-snapshot


**Example 2: To delete a cluster, allowing a final cluster snapshot**

This example deletes a cluster, but specifies a final cluster snapshot.

Command::

    aws redshift delete-cluster --cluster-identifier mycluster --final-cluster-snapshot-identifier myfinalsnapshot


