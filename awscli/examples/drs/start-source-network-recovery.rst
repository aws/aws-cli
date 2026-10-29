**To start source network recovery**

The following ``start-source-network-recovery`` example starts a recovery job for the specified source network. ::

    aws drs start-source-network-recovery \
        --source-networks '[{"sourceNetworkID":"sn-1234567890abcdef0"}]'

Output::

    {
        "job": {
            "arn": "arn:aws:drs:us-west-2:123456789012:job/drsjob-1234567890abcdef0",
            "creationDateTime": "2024-06-15T19:00:00.000Z",
            "jobID": "drsjob-1234567890abcdef0",
            "status": "PENDING",
            "tags": {},
            "type": "LAUNCH"
        }
    }

For more information, see `Source network recovery <https://docs.aws.amazon.com/drs/latest/userguide/source-network-recovery.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
