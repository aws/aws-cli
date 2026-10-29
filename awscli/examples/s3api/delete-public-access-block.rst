**To delete the block public access configuration for a bucket**

The following ``delete-public-access-block`` example removes the block public access configuration on the specified bucket. ::

    aws s3api delete-public-access-block \
        --bucket amzn-s3-demo-bucket

This command produces no output.

For more information, see `Blocking public access to your Amazon S3 storage <https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html>`__ in the *Amazon S3 User Guide*.
