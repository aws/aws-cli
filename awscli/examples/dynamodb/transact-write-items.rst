**To write items atomically to one or more tables**

The following ``transact-write-items`` example updates one item and deletes another. The operation fails if either operation fails, or if either item contains a ``Rating`` attribute. ::

    aws dynamodb transact-write-items \
        --transact-items file://transact-items.json

Contents of the ``transact-items.json`` file::

    [
        {
            "Update": {
                "Key": {
                    "Artist": {"S": "Acme Band"},
                    "SongTitle": {"S": "Happy Day"}
                },
                "UpdateExpression": "SET AlbumTitle = :newval",
                "ExpressionAttributeValues": {
                    ":newval": {"S": "Updated Album Title"}
                },
                "TableName": "MusicCollection",
                "ConditionExpression": "attribute_not_exists(Rating)"
            }
        },
        {
            "Delete": {
                "Key": {
                    "Artist": {"S": "No One You Know"},
                    "SongTitle": {"S": "Call Me Today"}
                },
                "TableName": "MusicCollection",
                "ConditionExpression": "attribute_not_exists(Rating)"
            }
        }
    ]

This command produces no output.

For more information, see `Managing Complex Workflows with DynamoDB Transactions <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transactions.html>`__ in the *Amazon DynamoDB Developer Guide*.
