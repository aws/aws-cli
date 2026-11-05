**To wait until a cluster is running**

The following ``wait`` example waits until a cluster with the cluster ID ``j-3SD91U2E1L2QX`` is up and running. ::

    aws emr wait cluster-running \
        --cluster-id j-3SD91U2E1L2QX

This command produces no output.

For more information, see `View Amazon EMR cluster status and details <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-manage-view-clusters.html>`__ in the *Amazon EMR Management Guide*.
