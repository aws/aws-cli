**To verify access to a bucket**

The following ``head-bucket`` example verifies access to a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api head-bucket \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "BucketRegion": "us-west-2",
        "AccessPointAlias": false
    }

If the bucket exists and you have access to it, the output contains the Region of the bucket. Otherwise, an error message will be shown. For example::

    A client error (404) occurred when calling the HeadBucket operation: Not Found

For more information, see `General purpose buckets overview <https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingBucket.html>`__ in the *Amazon S3 User Guide*.
