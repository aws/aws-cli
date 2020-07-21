**To retrieve multiple items atomically from one or more tables**

The following ``transact-get-items`` example retrieves multiple items atomically. ::

    aws dynamodb transact-get-items \
        --transact-items file://transact-items.json

Contents of ``transact-items.json``::

    [
        {
            "Get": {
                "Key": {
                    "Artist": {"S": "Acme Band"},
                    "SongTitle": {"S": "Happy Day"}
                },
                "TableName": "MusicCollection"
            }
        },
        {
            "Get": {
                "Key": {
                    "Artist": {"S": "No One You Know"},
                    "SongTitle": {"S": "Call Me Today"}
                },
                "TableName": "MusicCollection"
            }
        }
    ]

Output::

    {
        "Responses": [
            {
                "Item": {
                    "AlbumTitle": {
                        "S": "Songs About Life"
                    },
                    "Artist": {
                        "S": "Acme Band"
                    },
                    "SongTitle": {
                        "S": "Happy Day"
                    }
                }
            },
            {
                "Item": {
                    "AlbumTitle": {
                        "S": "Somewhat Famous"
                    },
                    "Artist": {
                        "S": "No One You Know"
                    },
                    "SongTitle": {
                        "S": "Call Me Today"
                    }
                }
            }
        ]
    }

For more information, see `Managing Complex Workflows with DynamoDB Transactions <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/transactions.html>`__ in the *Amazon DynamoDB Developer Guide*.
