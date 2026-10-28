**Example 1: To add an item to a table**

The following ``put`` example adds a new item to the *MusicCollection* table. This command produces no output. ::

    aws ddb put MusicCollection '{Artist: "No One You Know", SongTitle: "Call Me Today", AlbumTitle: "Somewhat Famous"}'

**Example 2: To add items to a table from a file**

The following ``put`` example adds two new items from a file to the *MusicCollection* table. This command produces no output. ::

    aws ddb put MusicCollection file://items.json

The items to add to the table are in a JSON file, ``items.json``.

Contents of ``items.json``::

    [
        {
            "Artist": "No One You Know",
            "SongTitle": "Call Me Today",
            "AlbumTitle": "Somewhat Famous"
        },
        {
            "Artist": "No One You Know",
            "SongTitle": "Scared of My Shadow",
            "AlbumTitle": "Blue Sky Blues"
        }
    ]

**Example 3: To add items to a table from stdin**

The following ``put`` example adds a new item to the *MusicCollection* table by reading it from
stdin. This command produces no output. ::

    echo '{Artist: "No One You Know", SongTitle: "Call Me Today"}' \
        | aws ddb put MusicCollection -

**Example 4: To add an item to a table with a conditional expression**

The following ``put`` example performs a one-line conditional operation.
This put call to the *MusicCollection* table succeeds only if the
artist "Obscure Indie Band" does not exist in the table. ::

    aws ddb put MusicCollection '{Artist: "Obscure Indie Band", SongTitle: "Atlas"}' \
        --condition 'attribute_not_exists(Artist)'

If the key already exists, you should see:

Output::

    A client error (ConditionalCheckFailedException) occurred when calling the PutItem operation: The conditional request failed
