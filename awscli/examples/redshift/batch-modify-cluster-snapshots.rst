**To modify a set of cluster snapshots**

The following ``batch-modify-cluster-snapshots`` example modifies the settings for a set of cluster snapshots. ::

    aws redshift batch-modify-cluster-snapshots \
        --snapshot-identifier-list mycluster-2019-11-06-16-31 mycluster-2019-11-06-16-32 \
        --manual-snapshot-retention-period 30

Output::

    {
        "Resources": [
            "mycluster-2019-11-06-16-31",
            "mycluster-2019-11-06-16-32"
        ],
        "Errors": []
    }

For more information, see `Amazon Redshift Snapshots <https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-snapshots.html>`__ in the *Amazon Redshift Cluster Management Guide*.
