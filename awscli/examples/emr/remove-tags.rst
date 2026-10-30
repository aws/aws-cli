**To remove a tag from a cluster**

The following ``remove-tags`` example removes a tag with the key ``prod`` from a cluster with the cluster ID ``j-3SD91U2E1L2QX``. ::

    aws emr remove-tags \
        --resource-id j-3SD91U2E1L2QX \
        --tag-keys prod

This command produces no output.

For more information, see `Tag and categorize Amazon EMR cluster resources <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-tags.html>`__ in the *Amazon EMR Management Guide*.
