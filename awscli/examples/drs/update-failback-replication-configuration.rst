**To update the failback replication configuration**

The following ``update-failback-replication-configuration`` example updates the bandwidth throttling for failback replication. ::

    aws drs update-failback-replication-configuration \
        --recovery-instance-id i-1234567890abcdef0 \
        --bandwidth-throttling 100

This command produces no output.

For more information, see `Performing a failback <https://docs.aws.amazon.com/drs/latest/userguide/failback.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
