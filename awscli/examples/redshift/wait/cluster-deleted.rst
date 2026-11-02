**To wait for cluster to be deleted**

The following ``wait cluster-deleted`` example pauses and continues only after it can confirm that the specified cluster is deleted. ::

    aws redshift wait cluster-deleted \
        --cluster-identifier mycluster

This command produces no output.

For more information, see `Amazon Redshift provisioned clusters <https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-clusters.html>`__ in the *Amazon Redshift Cluster Management Guide*.
