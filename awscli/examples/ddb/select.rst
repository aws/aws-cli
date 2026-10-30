**Example 1: To scan an entire table**

The following ``select`` example scans the entire *MusicCollection* table, and then narrows the
results to songs by the artist "No One You Know". For each item, only the album
title and song title are returned. ::

    aws ddb select MusicCollection \
        --projection 'SongTitle, AlbumTitle' \
        --filter 'Artist = "No One You Know"'

Output::

    Count: 2
    Items:
    - SongTitle: "Call Me Today"
      AlbumTitle: "Somewhat Famous"
    - SongTitle: "Scared of My Shadow"
      AlbumTitle: "Blue Sky Blues"
    ScannedCount: 3

For more information, see `Scanning tables in DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Scan.html>`__ in the *Amazon DynamoDB Developer Guide*.

**Example 2: To query for specific primary keys**

The following ``select`` example queries items in the *MusicCollection* table. The table has a
hash-and-range primary key (*Artist* and *SongTitle*), but this query only
specifies the hash key value. It returns song titles by the artist named "No
One You Know". ::

    aws ddb select MusicCollection \
        --projection SongTitle \
        --key-condition 'Artist = "No One You Know"'

Output::

    Count: 2
    Items:
    - SongTitle: "Call Me Today"
    - SongTitle: "Scared of My Shadow"
    ScannedCount: 2

For more information, see `Querying tables in DynamoDB <https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.html>`__ in the *Amazon DynamoDB Developer Guide*.
