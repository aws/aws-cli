**Example 1: To view a list of items (objects and folders) stored in a container**

The following ``list-items`` example displays a list of items (objects and folders) stored in the specified container. ::

    aws mediastore-data list-items \
        --endpoint https://aaabbbcccdddee.data.mediastore.us-west-2.amazonaws.com

Output::

    {
        "Items": [
            {
                "Type": "OBJECT",
                "ContentLength": 3784,
                "Name": "setup.jpg",
                "ETag": "2aa333bbcc8d8d22d777e999c88d4aa9eeeeee4dd89ff7f55555a555555da6d3",
                "ContentType": "image/jpeg",
                "LastModified": 1563571859.379
            },
            {
                "Type": "FOLDER",
                "Name": "events"
            }
        ]
    }

**Example 2: To view a list of items (objects and folders) stored in a folder**

The following ``list-items`` example displays a list of items (objects and folders) stored in the specified folder. ::

    aws mediastore-data list-items \
        --endpoint https://aaabbbcccdddee.data.mediastore.us-west-2.amazonaws.com \
        --path events/baseball

Output::

    {
        "Items": [
            {
                "ETag": "2aa333bbcc8d8d22d777e999c88d4aa9eeeeee4dd89ff7f55555a555555da6d3",
                "ContentType": "image/jpeg",
                "Type": "OBJECT",
                "ContentLength": 3860266,
                "LastModified": 1563573031.872,
                "Name": "setup.jpg"
            }
        ]
    }
