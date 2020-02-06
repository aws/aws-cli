**To create a table**

The following ``create-table`` example uses the specified attributes and key schema to create a table named ``MusicCollection``. ::

    aws dynamodb create-table \
        --table-name MusicCollection \
        --attribute-definitions AttributeName=Artist,AttributeType=S AttributeName=SongTitle,AttributeType=S \
        --key-schema AttributeName=Artist,KeyType=HASH AttributeName=SongTitle,KeyType=RANGE \
        --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 

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
                "WriteCapacityUnits": 5, 
                "ReadCapacityUnits": 5
            }, 
            "TableSizeBytes": 0, 
            "TableName": "MusicCollection", 
            "TableStatus": "CREATING", 
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

For more information, see `Basic Operations for Tables <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithTables.Basics.html>`__ in the *Amazon DynamoDB Developer Guide*.
