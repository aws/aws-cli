**To add an item to a table**

This example adds a new item to the *MusicCollection* table.

Command::

  aws dynamodb put-item --table-name MusicCollection --item file://item.json --return-consumed-capacity TOTAL 

The arguments for ``--item`` are stored in a JSON file, ``item.json``.  Here are the contents of that file::

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
