**To start a database activity stream**

The following ``start-activity-stream`` example starts an asynchronous activity stream to monitor an Aurora cluster named my-pg-cluster. ::

    aws rds start-activity-stream \
        --mode async \
        --kms-key-id arn:aws:kms:us-west-2:1234567890123:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --resource-arn arn:aws:rds:us-west-2:1234567890123:cluster:my-pg-cluster \
        --apply-immediately

Output::

    {
        "KmsKeyId": "arn:aws:kms:us-west-2:1234567890123:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "KinesisStreamName": "aws-rds-das-cluster-0ABCDEFGHI1JKLM2NOPQ3R4S",
        "Status": "starting",
        "Mode": "async",
        "ApplyImmediately": true
    }

For more information, see `Starting a database activity stream <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/DBActivityStreams.Enabling.html>`__ in the *Amazon Aurora User Guide*.