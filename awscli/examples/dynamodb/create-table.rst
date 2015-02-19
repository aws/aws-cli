**To create a table**

This example creates a table named *MusicCollection*.

Command::

  aws dynamodb create-table --table-name MusicCollection --attribute-definitions AttributeName=Artist,AttributeType=S AttributeName=SongTitle,AttributeType=S --key-schema AttributeName=Artist,KeyType=HASH AttributeName=SongTitle,KeyType=RANGE --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 

Output::

  {
      "TableDescription": {
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
          "TableStatus": "CREATING", 
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
