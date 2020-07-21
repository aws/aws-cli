**To read an item in a table**

The following ``get-item`` example retrieves an item from the ``MusicCollection`` table. The table has a hash-and-range primary key (``Artist`` and ``SongTitle``), so you must specify both of these attributes. ::

    aws dynamodb get-item \
        --table-name MusicCollection \
        --key file://key.json

Contents of ``key.json``::

    {
        "Artist": {"S": "Acme Band"},
        "SongTitle": {"S": "Happy Day"}
    }

Output::

    {
        "Item": {
            "AlbumTitle": {
                "S": "Songs About Life"
            }, 
            "SongTitle": {
                "S": "Happy Day"
            }, 
            "Artist": {
                "S": "Acme Band"
            }
        }
    }

For more information, see `Reading an Item <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.ReadingData>`__ in the *Amazon DynamoDB Developer Guide*.
