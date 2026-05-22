**To reverse replication for a recovery instance**

The following ``reverse-replication`` example starts reverse replication from the specified recovery instance back to the source. ::

    aws drs reverse-replication \
        --recovery-instance-id s-1234567890abcdef0

Output::

    {
        "reversedDirectionSourceServerArn": "arn:aws:drs:us-west-2:123456789012:source-server/s-0987654321fedcba0"
    }

For more information, see `Performing a failback <https://docs.aws.amazon.com/drs/latest/userguide/failback.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
