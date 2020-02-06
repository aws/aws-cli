**To modify a table's provisioned throughput**

The following ``update-table`` example increases the provisioned read and write capacity on the ``MusicCollection`` table. ::

    aws dynamodb update-table \
        --table-name MusicCollection \
        --provisioned-throughput ReadCapacityUnits=10,WriteCapacityUnits=10 

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
            "ProvisionedThroughput": {
                "NumberOfDecreasesToday": 0, 
                "WriteCapacityUnits": 1, 
                "LastIncreaseDateTime": 1421874759.194, 
                "ReadCapacityUnits": 1
            }, 
            "TableSizeBytes": 0, 
            "TableName": "MusicCollection", 
            "TableStatus": "UPDATING", 
            "KeySchema": [
                {
                    "KeyType": "HASH", 
                    "AttributeName": "Artist"
                }, 
                {
                    "KeyType": "RANGE", 
                    "AttributeName": "SongTitle"
                }
            ], 
            "ItemCount": 0, 
            "CreationDateTime": 1421866952.062
        }
    }

For more information, see `Updating a Table <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithTables.Basics.html#WorkingWithTables.Basics.UpdateTable>`__ in the *Amazon DynamoDB Developer Guide*.
