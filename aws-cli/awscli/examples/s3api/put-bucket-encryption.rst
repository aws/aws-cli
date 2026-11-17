**To configure server-side encryption for a bucket**

The following ``put-bucket-encryption`` example sets AES256 encryption as the default for the specified bucket. ::

    aws s3api put-bucket-encryption \
        --bucket amzn-s3-demo-bucket \
        --server-side-encryption-configuration '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'

This command produces no output.

For more information, see `Setting default server-side encryption behavior for Amazon S3 buckets <https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-encryption.html>`__ in the *Amazon S3 User Guide*.
