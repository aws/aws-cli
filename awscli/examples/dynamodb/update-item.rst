**To update an item in a table**

This example updates an item in the *MusicCollection* table. It adds a new attribute (*Year*) and modifies the *AlbumTitle* attribute.  All of the attributes in the item, as they appear after the update, are returned in the response.


Command::

  aws dynamodb update-item --table-name MusicCollection --key file://key.json --update-expression "SET #Y = :y, #AT = :t" --expression-attribute-names file://expression-attribute-names.json --expression-attribute-values file://expression-attribute-values.json  --return-values ALL_NEW

The arguments for ``--key`` are stored in a JSON file, ``key.json``.  Here are the contents of that file::

  {
      "Artist": {"S": "Acme Band"},
      "SongTitle": {"S": "Happy Day"}
  }


The arguments for ``--expression-attribute-names`` are stored in a JSON file, ``expression-attribute-names.json``.  Here are the contents of that file::

  {
      "#Y":"Year", "#AT":"AlbumTitle"
  }

The arguments for ``--expression-attribute-values`` are stored in a JSON file, ``expression-attribute-values.json``.  Here are the contents of that file::

  {
      ":y":{"N": "2015"},
      ":t":{"S": "Louder Than Ever"}
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
