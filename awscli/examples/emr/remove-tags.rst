**To remove a tag from a cluster**

The following ``remove-tags`` example removes a tag with the key ``prod`` from a cluster with the cluster ID ``j-3SD91U2E1L2QX``. This command produces no output. ::

    aws emr remove-tags \
        --resource-id j-3SD91U2E1L2QX \
        --tag-keys prod
