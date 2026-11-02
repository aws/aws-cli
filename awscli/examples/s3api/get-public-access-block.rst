**To set or modify the block public access configuration for a bucket**

The following ``get-public-access-block`` example displays the block public access configuration for the specified bucket. ::

    aws s3api get-public-access-block \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "PublicAccessBlockConfiguration": {
            "IgnorePublicAcls": true,
            "BlockPublicPolicy": true,
            "BlockPublicAcls": true,
            "RestrictPublicBuckets": true
        }
    }

For more information, see `Configuring block public access settings for your S3 buckets <https://docs.aws.amazon.com/AmazonS3/latest/userguide/configuring-block-public-access-bucket.html>`__ in the *Amazon S3 User Guide*.
