**To sets an analytics configuration for the bucket**

The following ``put-bucket-analytics-configuration`` example configures analytics for the specified bucket. ::

    aws s3api put-bucket-analytics-configuration \
        --bucket amzn-s3-demo-bucket \
        --id 1 \
        --analytics-configuration '{"Id": "1","StorageClassAnalysis": {}}'

This command produces no output.

For more information, see `Amazon S3 analytics - Storage Class Analysis <https://docs.aws.amazon.com/AmazonS3/latest/userguide/analytics-storage-class.html>`__ in the *Amazon S3 User Guide*.
