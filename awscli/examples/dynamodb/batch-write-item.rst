**To add multiple items to a table**

This example adds three new items to the *MusicCollection* table using a batch of three PutItem requests.

Command::

  aws dynamodb batch-write-item --request-items file://request-items.json

The arguments for ``--request-items`` are stored in a JSON file, ``request-items.json``.  Here are the contents of that file::

  {
      "MusicCollection": [
          { 
              "PutRequest": {
                  "Item": {
                      "Artist": {"S": "No One You Know"},
                      "SongTitle": {"S": "Call Me Today"},
                      "AlbumTitle": {"S": "Somewhat Famous"}
                  }
              }
          },
          {
              "PutRequest": {
                  "Item": {
                      "Artist": {"S": "Acme Band"},
                      "SongTitle": {"S": "Happy Day"},
                      "AlbumTitle": {"S": "Songs About Life"}
                  }
              }
          },
          {
              "PutRequest": {
                  "Item": {
                      "Artist": {"S": "No One You Know"},
                      "SongTitle": {"S": "Scared of My Shadow"},
                      "AlbumTitle": {"S": "Blue Sky Blues"}
                  }
              }
          }
      ]
  }

Output::

  {
      "UnprocessedItems": {}
  }
