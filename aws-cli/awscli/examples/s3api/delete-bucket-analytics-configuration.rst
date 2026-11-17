**To delete an analytics configuration for a bucket**

The following ``delete-bucket-analytics-configuration`` example removes the analytics configuration for the specified bucket and ID. ::

    aws s3api delete-bucket-analytics-configuration \
        --bucket amzn-s3-demo-bucket \
        --id 1

This command produces no output.

For more information, see `Amazon S3 analytics - Storage Class Analysis <https://docs.aws.amazon.com/AmazonS3/latest/userguide/analytics-storage-class.html>`__ in the *Amazon S3 User Guide*.
