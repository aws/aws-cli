**To deliver a configuration snapshot**

The following ``deliver-config-snapshot`` example delivers a configuration snapshot to the Amazon S3 bucket that belongs to the default delivery channel. ::

    aws configservice deliver-config-snapshot \
        --delivery-channel-name default

Output::

    {
        "configSnapshotId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Delivering Configuration Snapshots to an Amazon S3 Bucket <https://docs.aws.amazon.com/config/latest/developerguide/deliver-snapshot-cli.html>`__ in the *AWS Config Developer Guide*.
