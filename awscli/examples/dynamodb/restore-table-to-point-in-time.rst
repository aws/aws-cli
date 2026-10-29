**To restore a DynamoDB table to a point in time**

The following ``restore-table-to-point-in-time`` example restores the ``MusicCollection`` table to the specified point in time. ::

    aws dynamodb restore-table-to-point-in-time \
        --source-table-name MusicCollection \
        --target-table-name MusicCollectionRestore \
        --restore-date-time 1576622404.0

Output::

    {
        "TableDescription": {
            "AttributeDefinitions": [
                {
                    "AttributeName": "Artist",
                    "AttributeType": "S"
                },
                {
                    "AttributeName": "SongTitle",
                    "AttributeType": "S"
                }
            ],
            "TableName": "MusicCollectionRestore",
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
            "TableStatus": "CREATING",
            "CreationDateTime": 1576623311.86,
            "ProvisionedThroughput": {
                "NumberOfDecreasesToday": 0,
                "ReadCapacityUnits": 5,
                "WriteCapacityUnits": 5
            },
            "TableSizeBytes": 0,
            "ItemCount": 0,
            "TableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/MusicCollectionRestore",
            "TableId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "BillingModeSummary": {
                "BillingMode": "PROVISIONED"
            },
            "RestoreSummary": {
                "SourceTableArn": "arn:aws:dynamodb:us-west-2:123456789012:table/MusicCollection",
                "RestoreDateTime": 1576622404.0,
                "RestoreInProgress": true
            }
        }
    }

For more information, see `Point-in-time backups for DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Point-in-time-recovery.html>`__ in the *Amazon DynamoDB Developer Guide*.
