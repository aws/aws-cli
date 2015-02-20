**To read an item in a table**

This example retrieves an item from the *MusicCollection* table. The table has a hash-and-range primary key (*Artist* and *SongTitle*), so you must specify both of these ttributes.


Command::

  aws dynamodb get-item --table-name MusicCollection --key file://key.json

The arguments for ``--key`` are stored in a JSON file, ``key.json``.  Here are the contents of that file::

  {
      "Artist": {"S": "Acme Band"},
      "SongTitle": {"S": "Happy Day"}
  }


Output::

  {
      "Item": {
          "AlbumTitle": {
              "S": "Songs About Life"
          }, 
          "SongTitle": {
              "S": "Happy Day"
          }, 
          "Artist": {
              "S": "Acme Band"
          }
      }
  }
