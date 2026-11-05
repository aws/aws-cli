**To retrieve the accelerate configuration of a bucket**

The following ``get-bucket-accelerate-configuration`` example retrieves the accelerate configuration for the specified bucket. ::

    aws s3api get-bucket-accelerate-configuration \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "Status": "Enabled"
    }

For more information, see `Configuring fast, secure file transfers using Amazon S3 Transfer Acceleration <https://docs.aws.amazon.com/AmazonS3/latest/userguide/transfer-acceleration.html>`__ in the *Amazon S3 User Guide*.
