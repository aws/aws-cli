**To retrieve the object retention configuration for an object**

The following ``get-object-retention`` example retrieves the object retention configuration for the specified object. ::

    aws s3api get-object-retention \
        --bucket amzn-s3-demo-bucket \
        --key doc1.rtf

Output::

    {
        "Retention": {
            "Mode": "GOVERNANCE",
            "RetainUntilDate": "2025-01-01T00:00:00.000Z"
        }
    }

For more information, see `Locking objects with Object Lock <https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html>`__ in the *Amazon S3 User Guide*.
