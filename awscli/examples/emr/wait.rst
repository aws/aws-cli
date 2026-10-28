**To wait until a cluster is running**

The following ``wait`` example waits until a cluster with the cluster ID ``j-3SD91U2E1L2QX`` is up and running. This command produces no output. ::

    aws emr wait cluster-running \
        --cluster-id j-3SD91U2E1L2QX
