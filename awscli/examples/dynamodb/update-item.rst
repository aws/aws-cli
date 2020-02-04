**To update an item in a table**

The following ``update-table`` example updates an item in the ``MusicCollection`` table. It adds a new attribute (``Year``) and modifies the ``AlbumTitle`` attribute. All of the attributes in the item, as they appear after the update, are returned in the response. ::

    aws dynamodb update-item \
        --table-name MusicCollection \
        --key file://key.json \
        --update-expression "SET #Y = :y, #AT = :t" \
        --expression-attribute-names file://expression-attribute-names.json \
        --expression-attribute-values file://expression-attribute-values.json  \
        --return-values ALL_NEW

Contents of ``key.json``::

    {
        "Artist": {"S": "Acme Band"},
        "SongTitle": {"S": "Happy Day"}
    }

Contents of ``expression-attribute-names.json``::

    {
        "#Y":"Year", "#AT":"AlbumTitle"
    }

Contents of ``expression-attribute-values.json``::

    {
        ":y":{"N": "2015"},
        ":t":{"S": "Louder Than Ever"}
    }

Output::

    {
        "Item": {
            "AlbumTitle": {
                "S": "Louder Than Ever"
            },
            "SongTitle": {
                "S": "Happy Day"
            },
            "Artist": {
                "S": "Acme Band"
            },
            "Year": {
                "N" : "2015"
            }
        }
    }

For more information, see `Writing an Item <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.WritingData>`__ in the *Amazon DynamoDB Developer Guide*.
