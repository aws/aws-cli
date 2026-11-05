**To delete a bucket policy**

The following ``delete-bucket-policy`` example deletes a bucket policy from a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api delete-bucket-policy \
        --bucket amzn-s3-demo-bucket

This command produces no output.

For more information, see `Bucket policies for Amazon S3 <https://docs.aws.amazon.com/AmazonS3/latest/userguide/bucket-policies.html>`__ in the *Amazon S3 User Guide*.
