**To retrieve the location constraint of a bucket**

The following ``get-bucket-location`` example retrieves the location constraint for a bucket named ``amzn-s3-demo-bucket``, if a constraint exists. ::

    aws s3api get-bucket-location \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "LocationConstraint": "us-west-2"
    }

For more information, see `General purpose buckets overview <https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingBucket.html>`__ in the *Amazon S3 User Guide*.
