**To wait (pause running) until an object exists**

The following ``wait object-exists`` example pauses and continues only after it can confirm that the specified object (``--key``) in the specified bucket exists. ::

    aws s3api wait object-exists \
        --bucket amzn-s3-demo-bucket \
        --key doc1.rtf

This command produces no output.

For more information, see `Amazon S3 objects overview <https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingObjects.html>`__ in the *Amazon S3 User Guide*.
