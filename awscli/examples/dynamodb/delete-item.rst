**To delete an item**

The following ``delete-item`` example deletes an item from the ``MusicCollection`` table. ::

    aws dynamodb delete-item \
        --table-name MusicCollection \
        --key file://key.json

Contents of ``key.json``::

    {
        "Artist": {"S": "No One You Know"},
        "SongTitle": {"S": "Scared of My Shadow"}
    }

Output::

    {
        "ConsumedCapacity": {
            "CapacityUnits": 1.0, 
            "TableName": "MusicCollection"
        }
    }

For more information, see `Writing an Item <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.WritingData>`__ in the *Amazon DynamoDB Developer Guide*.
