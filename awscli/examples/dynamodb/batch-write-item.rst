**To add multiple items to a table**

The following ``batch-write-item`` example adds three new items to the ``MusicCollection`` table using a batch of three ``PutItem`` requests. ::

    aws dynamodb batch-write-item \
        --request-items file://request-items.json

Contents of ``request-items.json``::

    {
        "MusicCollection": [
            { 
                "PutRequest": {
                    "Item": {
                        "Artist": {"S": "No One You Know"},
                        "SongTitle": {"S": "Call Me Today"},
                        "AlbumTitle": {"S": "Somewhat Famous"}
                    }
                }
            },
            {
                "PutRequest": {
                    "Item": {
                        "Artist": {"S": "Acme Band"},
                        "SongTitle": {"S": "Happy Day"},
                        "AlbumTitle": {"S": "Songs About Life"}
                    }
                }
            },
            {
                "PutRequest": {
                    "Item": {
                        "Artist": {"S": "No One You Know"},
                        "SongTitle": {"S": "Scared of My Shadow"},
                        "AlbumTitle": {"S": "Blue Sky Blues"}
                    }
                }
            }
        ]
    }

Output::

    {
        "UnprocessedItems": {}
    }
    
For more information, see `Batch Operations <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.BatchOperations>`__ in the *Amazon DynamoDB Developer Guide*.
