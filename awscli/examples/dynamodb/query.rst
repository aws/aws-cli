**To query an item**

The following ``query`` example queries items in the ``MusicCollection`` table. The table has a hash-and-range primary key (``Artist`` and ``SongTitle``), but this query only specifies the hash key value. It returns song titles by the artist named "No One You Know". ::

    aws dynamodb query \
        --table-name MusicCollection \
        --projection-expression "SongTitle" \
        --key-condition-expression "Artist = :v1" \
        --expression-attribute-values file://expression-attributes.json

Contents of ``expression-attributes.json``::

    {
        ":v1": {"S": "No One You Know"}
    }

Output::

    {
        "Count": 2,
        "Items": [
            {
                "SongTitle": {
                    "S": "Call Me Today"
                },
                "SongTitle": {
                    "S": "Scared of My Shadow"
                }
            }
        ],
        "ScannedCount": 2,
        "ConsumedCapacity": null
    }

For more information, see `Working with Queries in DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.html>`__ in the *Amazon DynamoDB Developer Guide*.
