**To create a restore request for an object**

The following ``restore-object`` example restores the specified Amazon S3 Glacier object for the bucket ``amzn-s3-demo-bucket`` for 10 days. ::

    aws s3api restore-object \
        --bucket amzn-s3-demo-bucket \
        --key doc1.rtf \
        --restore-request Days=10

This command produces no output.

For more information, see `Restoring an archived object <https://docs.aws.amazon.com/AmazonS3/latest/userguide/restoring-objects.html>`__ in the *Amazon S3 User Guide*.
