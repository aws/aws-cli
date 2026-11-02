**Example 1: To enable ``requester pays`` configuration for a bucket**

The following ``put-bucket-request-payment`` example enables ``requester pays`` for the specified bucket. ::

    aws s3api put-bucket-request-payment \
        --bucket amzn-s3-demo-bucket \
        --request-payment-configuration '{"Payer":"Requester"}'

This command produces no output.

For more information, see `Using Requester Pays general purpose buckets for storage transfers and usage <https://docs.aws.amazon.com/AmazonS3/latest/userguide/RequesterPaysBuckets.html>`__ in the *Amazon S3 User Guide*.

**Example 2: To disable ``requester pays`` configuration for a bucket**

The following ``put-bucket-request-payment`` example disables ``requester pays`` for the specified bucket. ::

    aws s3api put-bucket-request-payment \
        --bucket amzn-s3-demo-bucket \
        --request-payment-configuration '{"Payer":"BucketOwner"}'

This command produces no output.

For more information, see `Using Requester Pays general purpose buckets for storage transfers and usage <https://docs.aws.amazon.com/AmazonS3/latest/userguide/RequesterPaysBuckets.html>`__ in the *Amazon S3 User Guide*.
