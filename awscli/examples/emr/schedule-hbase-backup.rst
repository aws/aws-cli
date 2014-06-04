**1. To schedule a full hbase backup**

- Command::

    aws emr schedule-hbase-backup --cluster-id j-XXXXXXYY --type full --dir
    s3://myBucket/backup --interval 10 --unit hours --start-time
    2014-04-21T05:26:10Z --consistent

- Output::

    None

**2. To schedule an incremental hbase backup**

- Command::

    aws emr schedule-hbase-backup --cluster-id j-XXXXXXYY --type incremental
     --dir s3://myBucket/backup --interval 30 --unit minutes --start-time
    2014-04-21T05:26:10Z --consistent

- Output::

    None