**To query an item**

This example queries items in the *MusicCollection* table. The table has a hash-and-range primary key (*Artist* and *SongTitle*), but this query only specifies the hash key value. It returns song titles by the artist named "No One You Know".

Command::

  aws dynamodb query --table-name MusicCollection --key-condition-expression "Artist = :v1 AND SongTitle = :v2" --expression-attribute-values file://expression-attributes.json

The arguments for ``--expression-attribute-values`` are stored in a JSON file named ``expression-attributes.json``::

  {
    ":v1": {"S": "No One You Know"},
    ":v2": {"S": "Call Me Today"}
  }

Output::

  {
      "Count": 1,
      "Items": [
          {
              "AlbumTitle": {
                  "S": "Somewhat Famous"
              },
              "SongTitle": {
                  "S": "Call Me Today"
              },
              "Artist": {
                  "S": "No One You Know"
              }
          }
      ],
      "ScannedCount": 1,
      "ConsumedCapacity": null
  }
