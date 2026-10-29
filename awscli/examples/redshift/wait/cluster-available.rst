**To wait for cluster to become available**

The following ``wait cluster-available`` example pauses and continues only after it can confirm that the specified cluster is available. ::

    aws redshift wait cluster-available \
        --cluster-identifier mycluster

This command produces no output.

For more information, see `Amazon Redshift provisioned clusters <https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-clusters.html>`__ in the *Amazon Redshift Cluster Management Guide*.
