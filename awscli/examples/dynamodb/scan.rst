**To scan a table**

This example scans the entire *MusicCollection* table, and then narrows the results to songs by the artist "No One You Know". For each item, only the album title and song title are returned. 

Command::

  aws dynamodb scan --table-name MusicCollection --filter-expression "Artist = :a" --projection-expression "#ST, #AT" --expression-attribute-names file://expression-attribute-names.json --expression-attribute-values file://expression-attribute-values.json 

The arguments for ``--expression-attribute-names`` are stored in a JSON file, ``expression-attribute-names.json``.  Here are the contents of that file::

  {
      "#ST": "SongTitle", 
      "#AT":"AlbumTitle"
  }


The arguments for ``--expression-attribute-values`` are stored in a JSON file, ``expression-attribute-values.json``.  Here are the contents of that file::

  {
      ":a": {"S": "No One You Know"}
  }

Output::

  {
      "Count": 2, 
      "Items": [
          {
              "SongTitle": {
                  "S": "Call Me Today"
              }, 
              "AlbumTitle": {
                  "S": "Somewhat Famous"
              }
          }, 
          {
              "SongTitle": {
                  "S": "Scared of My Shadow"
              }, 
              "AlbumTitle": {
                  "S": "Blue Sky Blues"
              }
          }
      ], 
      "ScannedCount": 3, 
      "ConsumedCapacity": null
  }
