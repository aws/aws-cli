**To set an object retention configuration for an object**

The following ``put-object-retention`` example sets an object retention configuration for the specified object until 2025-01-01. ::

    aws s3api put-object-retention \
        --bucket amzn-s3-demo-bucket \
        --key doc1.rtf \
        --retention '{ "Mode": "GOVERNANCE", "RetainUntilDate": "2025-01-01T00:00:00" }'

This command produces no output.

For more information, see `Locking objects with Object Lock <https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html>`__ in the *Amazon S3 User Guide*.
