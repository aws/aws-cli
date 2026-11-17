**To delete the lifecycle configuration of a bucket**

The following ``delete-bucket-lifecycle`` example deletes a lifecycle configuration from a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api delete-bucket-lifecycle \
        --bucket amzn-s3-demo-bucket

This command produces no output.

For more information, see `Managing the lifecycle of objects <https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lifecycle-mgmt.html>`__ in the *Amazon S3 User Guide*.
