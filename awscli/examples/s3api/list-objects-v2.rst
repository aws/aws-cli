**To get a list of objects in a bucket**

The following ``list-objects-v2`` example lists the objects in the specified bucket. ::

    aws s3api list-objects-v2 \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "Contents": [
            {
                "LastModified": "2019-11-05T23:11:50.000Z",
                "ETag": "\"621503c373607d548b37cff8778d992c\"",
                "StorageClass": "STANDARD",
                "Key": "doc1.rtf",
                "Size": 391
            },
            {
                "LastModified": "2019-11-05T23:11:50.000Z",
                "ETag": "\"a2cecc36ab7c7fe3a71a273b9d45b1b5\"",
                "StorageClass": "STANDARD",
                "Key": "doc2.rtf",
                "Size": 373
            },
            {
                "LastModified": "2019-11-05T23:11:50.000Z",
                "ETag": "\"08210852f65a2e9cb999972539a64d68\"",
                "StorageClass": "STANDARD",
                "Key": "doc3.rtf",
                "Size": 399
            },
            {
                "LastModified": "2019-11-05T23:11:50.000Z",
                "ETag": "\"d1852dd683f4043065a9471af106988e\"",
                "StorageClass": "STANDARD",
                "Key": "doc4.rtf",
                "Size": 6225
            }
        ]
    }

For more information, see `Listing object keys programmatically <https://docs.aws.amazon.com/AmazonS3/latest/userguide/ListingKeysUsingAPIs.html>`__ in the *Amazon S3 User Guide*.

**To list the immediate child prefixes under a prefix**

The following ``list-objects-v2`` example lists the child prefixes under ``photos/``. For example, if the bucket contains ``photos/2024/jan.jpg``, ``photos/2025/feb.jpg``, and ``photos/cover.jpg``, the output contains only the two year prefixes. ::

    aws s3api list-objects-v2 \
        --bucket amzn-s3-demo-bucket \
        --prefix photos/ \
        --delimiter / \
        --query 'CommonPrefixes[].Prefix' \
        --output json

Output::

    [
        "photos/2024/",
        "photos/2025/"
    ]

The delimiter groups keys at the next slash. The query selects those groups from ``CommonPrefixes``, so objects directly under ``photos/`` are omitted.
