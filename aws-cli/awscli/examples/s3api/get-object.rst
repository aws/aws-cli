**Example 1: To download an object**

The following ``get-object`` example downloads an object from Amazon S3. ::

    aws s3api get-object my_images.tar.bz2 \
        --bucket amzn-s3-demo-bucket \
        --key dir/my_images.tar.bz2

Output::

    {
        "AcceptRanges": "bytes",
        "LastModified": "2015-04-16T18:19:14+00:00",
        "ContentLength": 3191,
        "ETag": "\"30a6ec7e1a9ad79c203d05a589c8b400\"",
        "ContentType": "binary/octet-stream",
        "ServerSideEncryption": "AES256",
        "Metadata": {}
    }

Note that the outfile parameter is specified without an option name such as "--outfile".

**Example 2: To download a specific byte range from an object**

The following ``get-object`` example uses ``--range`` to download a specific byte range from an object. Note the byte ranges need to be prefixed with "bytes=". ::

    aws s3api get-object my_data_range \
        --bucket amzn-s3-demo-bucket \
        --key dir/my_data \
        --range bytes=8888-9999

Output::

    {
        "AcceptRanges": "bytes",
        "LastModified": "2015-04-16T18:21:07+00:00",
        "ContentLength": 1112,
        "ETag": "\"0db5e5a2c4f0b9d3e1f6a7b8c9d0e1f2\"",
        "ContentRange": "bytes 8888-9999/20000",
        "ContentType": "binary/octet-stream",
        "ServerSideEncryption": "AES256",
        "Metadata": {}
    }

For more information, see `Downloading objects <https://docs.aws.amazon.com/AmazonS3/latest/userguide/download-objects.html>`__ in the *Amazon S3 User Guide*.
