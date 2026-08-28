**To describe recovery jobs**

The following ``describe-jobs`` example describes all recovery jobs in your account. ::

    aws drs describe-jobs

Output::

    {
        "items": [
            {
                "arn": "arn:aws:drs:us-west-2:123456789012:job/drsjob-1234567890abcdef0",
                "creationDateTime": "2024-06-15T15:00:00.000Z",
                "endDateTime": "2024-06-15T15:36:12.000Z",
                "initiatedBy": "START_RECOVERY",
                "jobID": "drsjob-1234567890abcdef0",
                "participatingResources": [],
                "participatingServers": [
                    {
                        "launchStatus": "LAUNCHED",
                        "sourceServerID": "s-1234567890abcdef0"
                    }
                ],
                "status": "COMPLETED",
                "tags": {},
                "type": "LAUNCH"
            }
        ]
    }

For more information, see `Monitoring and managing jobs <https://docs.aws.amazon.com/drs/latest/userguide/managing-jobs.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
