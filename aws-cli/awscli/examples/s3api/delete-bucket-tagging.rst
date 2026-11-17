**To delete the tagging configuration of a bucket**

The following ``delete-bucket-tagging`` example deletes a tagging configuration from a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api delete-bucket-tagging \
        --bucket amzn-s3-demo-bucket

This command produces no output.

For more information, see `Using cost allocation S3 bucket tags <https://docs.aws.amazon.com/AmazonS3/latest/userguide/CostAllocTagging.html>`__ in the *Amazon S3 User Guide*.
