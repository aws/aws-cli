**To wait for cluster to be restored**

The following ``wait cluster-restored`` example pauses and resumes only after the CLI can confirm that the specified cluster is restored. ::

    aws redshift wait cluster-restored \
        --cluster-identifier mycluster

This command produces no output.

For more information, see `Amazon Redshift snapshots and backups <https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-snapshots.html>`__ in the *Amazon Redshift Cluster Management Guide*.
