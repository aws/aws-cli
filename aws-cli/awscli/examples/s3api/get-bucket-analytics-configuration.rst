**To retrieve the analytics configuration for a bucket with a specific ID**

The following ``get-bucket-analytics-configuration`` example displays the analytics configuration for the specified bucket and ID. ::

    aws s3api get-bucket-analytics-configuration \
        --bucket amzn-s3-demo-bucket \
        --id 1

Output::

    {
        "AnalyticsConfiguration": {
            "StorageClassAnalysis": {},
            "Id": "1"
        }
    }

For more information, see `Amazon S3 analytics - Storage Class Analysis <https://docs.aws.amazon.com/AmazonS3/latest/userguide/analytics-storage-class.html>`__ in the *Amazon S3 User Guide*.
