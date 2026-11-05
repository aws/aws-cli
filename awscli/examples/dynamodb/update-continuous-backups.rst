**To update continuous backup settings for a DynamoDB table**

The following ``update-continuous-backups`` example enables point-in-time recovery for the ``MusicCollection`` table. ::

    aws dynamodb update-continuous-backups \
        --table-name MusicCollection \
        --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true

Output::

    {
        "ContinuousBackupsDescription": {
            "ContinuousBackupsStatus": "ENABLED",
            "PointInTimeRecoveryDescription": {
                "PointInTimeRecoveryStatus": "ENABLED",
                "EarliestRestorableDateTime": 1576622404.0,
                "LatestRestorableDateTime": 1576622404.0
            }
        }
    }

For more information, see `Point-in-time backups for DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Point-in-time-recovery.html>`__ in the *Amazon DynamoDB Developer Guide*.