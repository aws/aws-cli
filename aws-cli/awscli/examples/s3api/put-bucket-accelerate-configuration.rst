**To set the accelerate configuration of a bucket**

The following ``put-bucket-accelerate-configuration`` example enables the accelerate configuration for the specified bucket. ::

    aws s3api put-bucket-accelerate-configuration \
        --bucket amzn-s3-demo-bucket \
        --accelerate-configuration Status=Enabled

This command produces no output.

For more information, see `Configuring fast, secure file transfers using Amazon S3 Transfer Acceleration <https://docs.aws.amazon.com/AmazonS3/latest/userguide/transfer-acceleration.html>`__ in the *Amazon S3 User Guide*.
