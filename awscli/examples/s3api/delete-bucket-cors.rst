**To delete the CORS configuration of a bucket**

The following ``delete-bucket-cors`` example deletes a Cross-Origin Resource Sharing configuration from a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api delete-bucket-cors \
        --bucket amzn-s3-demo-bucket

This command produces no output.

For more information, see `Using cross-origin resource sharing (CORS) <https://docs.aws.amazon.com/AmazonS3/latest/userguide/cors.html>`__ in the *Amazon S3 User Guide*.
