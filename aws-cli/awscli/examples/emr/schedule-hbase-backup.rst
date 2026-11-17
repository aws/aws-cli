**Example 1: To schedule a full HBase backup**

The following ``schedule-hbase-backup`` example schedules a full, consistent HBase backup to Amazon S3 every 10 hours. This command can only be used with HBase on AMI version 2.x and 3.x. The command adds an HBase backup step to the cluster and returns the ID of the step. ::

    aws emr schedule-hbase-backup \
        --cluster-id j-XXXXXXYY \
        --type full \
        --dir s3://amzn-s3-demo-bucket/backup \
        --interval 10 \
        --unit hours \
        --start-time 2014-04-21T05:26:10Z \
        --consistent

Output::

    {
        "StepIds": [
            "s-1A2B3C4D5E6F7"
        ]
    }

**Example 2: To schedule an incremental HBase backup**

The following ``schedule-hbase-backup`` example schedules an incremental, consistent HBase backup to Amazon S3 every 30 minutes. This command can only be used with HBase on AMI version 2.x and 3.x. The command adds an HBase backup step to the cluster and returns the ID of the step. ::

    aws emr schedule-hbase-backup \
        --cluster-id j-XXXXXXYY \
        --type incremental \
        --dir s3://amzn-s3-demo-bucket/backup \
        --interval 30 \
        --unit minutes \
        --start-time 2014-04-21T05:26:10Z \
        --consistent

Output::

    {
        "StepIds": [
            "s-2B3C4D5E6F7G8"
        ]
    }

For more information, see `HBase application specifics for earlier AMI versions of Amazon EMR <https://docs.aws.amazon.com/emr/latest/ReleaseGuide/emr-3x-hbase.html>`__ in the *Amazon EMR Release Guide*.
