**To delete the replication configuration of a bucket**

The following ``delete-bucket-replication`` example deletes a replication configuration from a bucket named ``amzn-s3-demo-bucket``. ::

    aws s3api delete-bucket-replication \
        --bucket amzn-s3-demo-bucket

This command produces no output.

For more information, see `Replicating objects within and across Regions <https://docs.aws.amazon.com/AmazonS3/latest/userguide/replication.html>`__ in the *Amazon S3 User Guide*.
