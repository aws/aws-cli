**To retrieve multiple items from a table**

The following ``batch-get-items`` example reads multiple items from the ``MusicCollection`` table using a batch of three ``GetItem`` requests. The command returns only the ``AlbumTitle`` attribute. ::

    aws dynamodb batch-get-item \
        --request-items file://request-items.json

Contents of ``request-items.json``::

    {
        "MusicCollection": {
            "Keys": [
                {
                    "Artist": {"S": "No One You Know"},
                    "SongTitle": {"S": "Call Me Today"}
                },
                {
                    "Artist": {"S": "Acme Band"},
                    "SongTitle": {"S": "Happy Day"}
                },
                {
                    "Artist": {"S": "No One You Know"},
                    "SongTitle": {"S": "Scared of My Shadow"}
                }
            ],
            "ProjectionExpression":"AlbumTitle"
        }
    }

Output::

    {
        "UnprocessedKeys": {}, 
        "Responses": {
            "MusicCollection": [
                {
                    "AlbumTitle": {
                        "S": "Somewhat Famous"
                    }
                }, 
                {
                    "AlbumTitle": {
                        "S": "Blue Sky Blues"
                    }
                }, 
                {
                    "AlbumTitle": {
                        "S": "Louder Than Ever"
                    }
                }
            ]
        }
    }

For more information, see `Batch Operations <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.BatchOperations>`__ in the *Amazon DynamoDB Developer Guide*.
