**To query an item**

This example queries items in the *MusicCollection* table. The table has a hash-and-range primary key (*Artist* and *SongTitle*), but this query only specifies the hash key value. It returns song titles by the artist named "No One You Know".

Command::

  aws dynamodb query --table-name MusicCollection --key-conditions file://key-conditions.json --projection-expression "SongTitle"

The arguments for ``--key-conditions`` are stored in a JSON file, ``key-conditions.json``.  Here are the contents of that file::

  { 
      "Artist": { 
          "AttributeValueList": [ 
              {"S": "No One You Know"}
          ],  
          "ComparisonOperator": "EQ" 
      } 
  }

Output::

  {
      "Count": 2, 
      "Items": [
          {
              "SongTitle": {
                  "S": "Call Me Today"
              }
          }, 
          {
              "SongTitle": {
                  "S": "Scared of My Shadow"
              }
          }
      ], 
      "ScannedCount": 2, 
      "ConsumedCapacity": null
  }
