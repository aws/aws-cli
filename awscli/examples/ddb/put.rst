**Example 1: To add an item to a table**

The following ``put`` example adds a new item to the *MusicCollection* table. ::

    aws ddb put MusicCollection '{Artist: "No One You Know", SongTitle: "Call Me Today", AlbumTitle: "Somewhat Famous"}'

This command produces no output.

For more information, see `Working with items and attributes in DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html>`__ in the *Amazon DynamoDB Developer Guide*.

**Example 2: To add items to a table from a file**

The following ``put`` example adds two new items from a file to the *MusicCollection* table. ::

    aws ddb put MusicCollection file://items.json

This command produces no output.

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

For more information, see `Working with items and attributes in DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html>`__ in the *Amazon DynamoDB Developer Guide*.

**Example 3: To add items to a table from stdin**

The following ``put`` example adds a new item to the *MusicCollection* table by reading it from
stdin. ::

    echo '{Artist: "No One You Know", SongTitle: "Call Me Today"}' \
        | aws ddb put MusicCollection -

This command produces no output.

For more information, see `Working with items and attributes in DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html>`__ in the *Amazon DynamoDB Developer Guide*.

**Example 4: To add an item to a table with a conditional expression**

The following ``put`` example performs a one-line conditional operation.
This put call to the *MusicCollection* table succeeds only if the
artist "Obscure Indie Band" does not exist in the table. ::

    aws ddb put MusicCollection '{Artist: "Obscure Indie Band", SongTitle: "Atlas"}' \
        --condition 'attribute_not_exists(Artist)'

If the key already exists, you should see:

Output::

    A client error (ConditionalCheckFailedException) occurred when calling the PutItem operation: The conditional request failed

For more information, see `DynamoDB condition expression CLI example <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html>`__ in the *Amazon DynamoDB Developer Guide*.
