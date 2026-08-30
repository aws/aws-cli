**To terminate recovery instances**

The following ``terminate-recovery-instances`` example terminates the specified recovery instances. ::

    aws drs terminate-recovery-instances \
        --recovery-instance-i-ds s-1234567890abcdef0

Output::

    {
        "job": {
            "arn": "arn:aws:drs:us-west-2:123456789012:job/drsjob-1234567890abcdef0",
            "creationDateTime": "2024-06-15T16:00:00.000Z",
            "jobID": "drsjob-1234567890abcdef0",
            "participatingServers": [
                {
                    "launchStatus": "PENDING",
                    "sourceServerID": "s-1234567890abcdef0"
                }
            ],
            "status": "PENDING",
            "tags": {},
            "type": "TERMINATE"
        }
    }

For more information, see `Managing recovery instances <https://docs.aws.amazon.com/drs/latest/userguide/recovery-instances.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
