**To retrieve multiple items from a table**

This example reads multiple items from the *MusicCollection* table using a batch of three GetItem requests.  Only the *AlbumTitle* attribute is returned.

Command::

  aws dynamodb batch-get-item --request-items file://request-items.json

The arguments for ``--request-items`` are stored in a JSON file, ``request-items.json``.  Here are the contents of that file::

  {
      "MusicCollection": {
          "Keys": [
              {
                  "Artist": {"S": "No One You Know"},
                  "SongTitle": {"S": "Call Me Today"}
              },
              {
                  "Artist": {"S": "Acme Band"},
                  "SongTitle": {"S": "Happy Day"}
              },
              {
                  "Artist": {"S": "No One You Know"},
                  "SongTitle": {"S": "Scared of My Shadow"}
              }
          ],
          "ProjectionExpression":"AlbumTitle"
      }
  }

Output::

  {
      "UnprocessedKeys": {}, 
      "Responses": {
          "MusicCollection": [
              {
                  "AlbumTitle": {
                      "S": "Somewhat Famous"
                  }
              }, 
              {
                  "AlbumTitle": {
                      "S": "Blue Sky Blues"
                  }
              }, 
              {
                  "AlbumTitle": {
                      "S": "Louder Than Ever"
                  }
              }
          ]
      }
  }
