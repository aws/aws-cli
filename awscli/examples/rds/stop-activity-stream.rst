**To stop a database activity stream**

The following ``stop-activity-stream`` example stops an activity stream in an Aurora cluster named my-pg-cluster. ::

    aws rds stop-activity-stream \
        --resource-arn arn:aws:rds:us-west-2:1234567890123:cluster:my-pg-cluster \
        --apply-immediately

Output::

    {
        "KmsKeyId": "arn:aws:kms:us-west-2:1234567890123:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "KinesisStreamName": "aws-rds-das-cluster-0ABCDEFGHI1JKLM2NOPQ3R4S",
        "Status": "stopping"
    }

For more information, see `Stopping an activity stream <https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/DBActivityStreams.Disabling.html>`__ in the *Amazon Aurora User Guide*.