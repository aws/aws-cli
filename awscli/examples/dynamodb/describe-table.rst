**To describe a table**

This example describes the *MusicCollection* table.

Command::

  aws dynamodb describe-table --table-name MusicCollection

Output::

  {
      "Table": {
          "AttributeDefinitions": [
              {
                  "AttributeName": "Artist", 
                  "AttributeType": "S"
              }, 
              {
                  "AttributeName": "SongTitle", 
                  "AttributeType": "S"
              }
          ], 
          "ProvisionedThroughput": {
              "NumberOfDecreasesToday": 0, 
              "WriteCapacityUnits": 5, 
              "ReadCapacityUnits": 5
          }, 
          "TableSizeBytes": 0, 
          "TableName": "MusicCollection", 
          "TableStatus": "ACTIVE", 
          "KeySchema": [
              {
                  "KeyType": "HASH", 
                  "AttributeName": "Artist"
              }, 
              {
                  "KeyType": "RANGE", 
                  "AttributeName": "SongTitle"
              }
          ], 
          "ItemCount": 0, 
          "CreationDateTime": 1421866952.062
      }
  }
