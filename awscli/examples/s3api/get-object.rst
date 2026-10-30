**Example 1: To download an object**

The following ``get-object`` example downloads an object from Amazon S3. ::

    aws s3api get-object my_images.tar.bz2 \
        --bucket text-content \
        --key dir/my_images.tar.bz2

Note that the outfile parameter is specified without an option name such as "--outfile".

**Example 2: To download a specific byte range from an object**

The following ``get-object`` example uses ``--range`` to download a specific byte range from an object. Note the byte ranges need to be prefixed with "bytes=". ::

    aws s3api get-object my_data_range \
        --bucket text-content \
        --key dir/my_data \
        --range bytes=8888-9999

For more information about retrieving objects, see `Getting Objects`_ in the *Amazon S3 Developer Guide*.

.. _`Getting Objects`: http://docs.aws.amazon.com/AmazonS3/latest/dev/GettingObjectsUsingAPIs.html
