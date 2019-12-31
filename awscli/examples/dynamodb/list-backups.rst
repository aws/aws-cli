**To list existing DynamoDB backups**

The following ``list-backups`` example lists all of your existing backups. ::

    aws dynamodb list-backups

Output::

    {
        "BackupSummaries": [
            {
                "TableName": "MusicCollection",
                "TableId": "b0c04bcc-309b-4352-b2ae-9088af169fe2",
                "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/MusicCollection",
                "BackupArn": "arn:aws:dynamodb:us-west-2:123456789012:table/MusicCollection/backup/01576616366715-b4e58d3a",
                "BackupName": "MusicCollectionBackup",
                "BackupCreationDateTime": 1576616366.715,
                "BackupStatus": "AVAILABLE",
                "BackupType": "USER",
                "BackupSizeBytes": 0
            }
        ]
    }

For more information, see `On-Demand Backup and Restore for DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BackupRestore.html>`__ in the *Amazon DynamoDB Developer Guide*.
