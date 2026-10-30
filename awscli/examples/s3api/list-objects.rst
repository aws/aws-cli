**To list the objects in a bucket**

The following ``list-objects`` example displays the names of all the objects in the specified bucket. ::

    aws s3api list-objects \
        --bucket amzn-s3-demo-bucket \
        --query 'Contents[].{Key: Key, Size: Size}'

Output::

    [
        {
            "Key": "dir/my_data",
            "Size": 20000
        },
        {
            "Key": "dir/my_images.tar.bz2",
            "Size": 3191
        }
    ]

The example uses the ``--query`` argument to filter the output of
``list-objects`` down to the key value and size for each object

For more information, see `Listing object keys programmatically <https://docs.aws.amazon.com/AmazonS3/latest/userguide/ListingKeysUsingAPIs.html>`__ in the *Amazon S3 User Guide*.
