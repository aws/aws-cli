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


**Conditional Expressions**

This example shows how to perform a one-line conditional expression operation. This put-item call to the table *MusicCollection* table will only succeed if the artist "Obscure Indie Band" does not exist in the table.

Command::

  aws dynamodb put-item --table-name MusicCollection --item '{"Artist": {"S": "Obscure Indie Band"}}' --condition-expression "attribute_not_exists(Artist)"


If the key already exists, you should see:

Output::

  A client error (ConditionalCheckFailedException) occurred when calling the PutItem operation: The conditional request failed
