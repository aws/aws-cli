**To retrieve the Legal Hold status of an object**

The following ``get-object-legal-hold`` example retrieves the Legal Hold status for the specified object. ::

    aws s3api get-object-legal-hold \
        --bucket amzn-s3-demo-bucket \
        --key doc1.rtf

Output::

    {
        "LegalHold": {
            "Status": "ON"
        }
    }

For more information, see `Locking objects with Object Lock <https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html>`__ in the *Amazon S3 User Guide*.
