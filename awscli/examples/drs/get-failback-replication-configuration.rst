**To get the failback replication configuration**

The following ``get-failback-replication-configuration`` example gets the failback replication configuration for the specified recovery instance. ::

    aws drs get-failback-replication-configuration \
        --recovery-instance-id i-1234567890abcdef0

Output::

    {
        "bandwidthThrottling": 0,
        "name": "Failback Replication Configuration",
        "recoveryInstanceID": "s-1234567890abcdef0",
        "usePrivateIP": false
    }

For more information, see `Performing a failback <https://docs.aws.amazon.com/drs/latest/userguide/failback.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
