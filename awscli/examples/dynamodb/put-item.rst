**Example1: To add an item to a table**

The following ``put-item`` example adds a new item to the *MusicCollection* table. ::

    aws dynamodb put-item \
        --table-name MusicCollection \
        --item file://item.json \
        --return-consumed-capacity TOTAL

Contents of ``item.json``::

    {
        "Artist": {"S": "No One You Know"},
        "SongTitle": {"S": "Call Me Today"},
        "AlbumTitle": {"S": "Somewhat Famous"}
    }

Output::

    {
        "ConsumedCapacity": {
            "CapacityUnits": 1.0,
            "TableName": "MusicCollection"
        }
    }

For more information, see `Writing an Item <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.WritingData>`__ in the *Amazon DynamoDB Developer Guide*.

**Example2: To add an item to a table conditionally**

The following ``put-item`` example adds a new item to the ``MusicCollection`` table only if the artist "Obscure Indie Band" does not already exist in the table. ::

    aws dynamodb put-item \
        --table-name MusicCollection \
        --item '{"Artist": {"S": "Obscure Indie Band"}}' \
        --condition-expression "attribute_not_exists(Artist)"

If the key already exists, you should see the following output::

    A client error (ConditionalCheckFailedException) occurred when calling the PutItem operation: The conditional request failed.

For more information, see `Condition Expressions <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html>`__ in the *Amazon DynamoDB Developer Guide*.
