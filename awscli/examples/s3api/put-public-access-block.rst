**To set the block public access configuration for a bucket**

The following ``put-public-access-block`` example sets a restrictive block public access configuration for the specified bucket. ::

    aws s3api put-public-access-block \
        --bucket amzn-s3-demo-bucket \
        --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

This command produces no output.

For more information, see `Blocking public access to your Amazon S3 storage <https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html>`__ in the *Amazon S3 User Guide*.
