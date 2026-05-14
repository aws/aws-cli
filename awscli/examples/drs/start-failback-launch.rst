**To start a failback launch**

The following ``start-failback-launch`` example starts a failback launch for the specified recovery instances. ::

    aws drs start-failback-launch \
        --recovery-instance-i-ds s-1234567890abcdef0

Output::

    {
        "job": {
            "arn": "arn:aws:drs:us-west-2:123456789012:job/drsjob-1234567890abcdef0",
            "creationDateTime": "2024-06-15T17:00:00.000Z",
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

For more information, see `Performing a failback <https://docs.aws.amazon.com/drs/latest/userguide/failback.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
