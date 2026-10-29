**To delete the server-side encryption configuration of a bucket**

The following ``delete-bucket-encryption`` example deletes the server-side encryption configuration of the specified bucket. ::

    aws s3api delete-bucket-encryption \
        --bucket amzn-s3-demo-bucket

This command produces no output.

For more information, see `Setting default server-side encryption behavior for Amazon S3 buckets <https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-encryption.html>`__ in the *Amazon S3 User Guide*.
