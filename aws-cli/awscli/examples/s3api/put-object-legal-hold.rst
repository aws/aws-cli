**To apply a Legal Hold to an object**

The following ``put-object-legal-hold`` example sets a Legal Hold on the object ``doc1.rtf``. ::

    aws s3api put-object-legal-hold \
        --bucket amzn-s3-demo-bucket \
        --key doc1.rtf \
        --legal-hold Status=ON

This command produces no output.

For more information, see `Locking objects with Object Lock <https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html>`__ in the *Amazon S3 User Guide*.
