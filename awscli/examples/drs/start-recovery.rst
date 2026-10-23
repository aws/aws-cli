**To start a recovery job**

The following ``start-recovery`` example starts a recovery job for the specified source servers. ::

    aws drs start-recovery \
        --source-servers '[{"sourceServerID":"s-1234567890abcdef0"}]'

Output::

    {
        "job": {
            "arn": "arn:aws:drs:us-west-2:123456789012:job/drsjob-1234567890abcdef0",
            "creationDateTime": "2024-06-15T15:00:00.000Z",
            "jobID": "drsjob-1234567890abcdef0",
            "participatingServers": [
                {
                    "launchStatus": "PENDING",
                    "sourceServerID": "s-1234567890abcdef0"
                }
            ],
            "status": "PENDING",
            "tags": {},
            "type": "LAUNCH"
        }
    }

For more information, see `Performing a recovery <https://docs.aws.amazon.com/drs/latest/userguide/recovery.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
