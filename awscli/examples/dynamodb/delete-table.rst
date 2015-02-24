**To delete a table**

This example deletes the *MusicCollection* table.

Command::

  aws dynamodb delete-table --table-name MusicCollection

Output::

  {
      "TableDescription": {
          "TableStatus": "DELETING", 
          "TableSizeBytes": 0, 
          "ItemCount": 0, 
          "TableName": "MusicCollection", 
          "ProvisionedThroughput": {
              "NumberOfDecreasesToday": 0, 
              "WriteCapacityUnits": 5, 
              "ReadCapacityUnits": 5
          }
      }
  }
