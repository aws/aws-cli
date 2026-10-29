**To view the headers for an object**

The following ``describe-object`` example displays the headers for an object at the specified path. ::

    aws mediastore-data describe-object \
        --endpoint https://aaabbbcccdddee.data.mediastore.us-west-2.amazonaws.com \
        --path events/baseball/setup.jpg

Output::

    {
        "LastModified": "Fri, 19 Jul 2019 21:50:31 GMT",
        "ContentType": "image/jpeg",
        "ContentLength": 3860266,
        "ETag": "2aa333bbcc8d8d22d777e999c88d4aa9eeeeee4dd89ff7f55555a555555da6d3"
    }
