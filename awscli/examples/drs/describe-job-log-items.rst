**To describe job log items**

The following ``describe-job-log-items`` example describes the log items for the specified recovery job. ::

    aws drs describe-job-log-items \
        --job-id drsjob-1234567890abcdef0

Output::

    {
        "items": [
            {
                "event": "JOB_START",
                "eventData": {},
                "logDateTime": "2024-06-15T15:00:00.000Z"
            },
            {
                "event": "SNAPSHOT_START",
                "eventData": {
                    "sourceServerID": "s-1234567890abcdef0"
                },
                "logDateTime": "2024-06-15T15:00:01.000Z"
            },
            {
                "event": "SNAPSHOT_END",
                "eventData": {
                    "sourceServerID": "s-1234567890abcdef0"
                },
                "logDateTime": "2024-06-15T15:00:05.000Z"
            },
            {
                "event": "JOB_END",
                "eventData": {},
                "logDateTime": "2024-06-15T15:36:12.000Z"
            }
        ]
    }

For more information, see `Monitoring and managing jobs <https://docs.aws.amazon.com/drs/latest/userguide/managing-jobs.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
