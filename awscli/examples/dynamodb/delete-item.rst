**To delete an item**

This example deletes an item from the *MusicCollection* table.

Command::

  aws dynamodb delete-item --table-name MusicCollection --key file://key.json

The arguments for ``--key`` are stored in a JSON file, ``key.json``.  Here are the contents of that file::

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
