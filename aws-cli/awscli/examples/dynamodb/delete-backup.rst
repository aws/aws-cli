**To delete an existing DynamoDB backup**

The following ``delete-backup`` example deletes the specified existing backup. ::

    aws dynamodb delete-backup \
        --backup-arn arn:aws:dynamodb:us-west-2:123456789012:table/MusicCollection/backup/01576616366715-b4e58d3a

Output::

    {
        "BackupDescription": {
            "BackupDetails": {
                "BackupArn": "arn:aws:dynamodb:us-west-2:123456789012:table/MusicCollection/backup/01576616366715-b4e58d3a",
                "BackupName": "MusicCollectionBackup",
                "BackupSizeBytes": 0,
                "BackupStatus": "DELETED",
                "BackupType": "USER",
                "BackupCreationDateTime": 1576616366.715
            },
            "SourceTableDetails": {
                "TableName": "MusicCollection",
                "TableId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/MusicCollection",
                "TableSizeBytes": 0,
                "KeySchema": [
                    {
                        "AttributeName": "Artist",
                        "KeyType": "HASH"
                    },
                    {
                        "AttributeName": "SongTitle",
                        "KeyType": "RANGE"
                    }
                ],
                "TableCreationDateTime": 1576615228.571,
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5
                },
                "ItemCount": 0,
                "BillingMode": "PROVISIONED"
            },
            "SourceTableFeatureDetails": {}
        }
    }

For more information, see `Backup and restore for DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Backup-and-Restore.html>`__ in the *Amazon DynamoDB Developer Guide*.
