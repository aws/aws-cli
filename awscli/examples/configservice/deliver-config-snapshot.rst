**To deliver a configuration snapshot**

The following ``deliver-config-snapshot`` example delivers a configuration snapshot to the Amazon S3 bucket that belongs to the default delivery channel. ::

    aws configservice deliver-config-snapshot --delivery-channel-name default

Output::

    {
        "configSnapshotId": "d0333b00-a683-44af-921e-examplefb794"
    }