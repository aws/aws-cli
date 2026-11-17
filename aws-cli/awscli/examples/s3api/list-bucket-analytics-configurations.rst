**To retrieve a list of analytics configurations for a bucket**

The following ``list-bucket-analytics-configurations`` example retrieves a list of analytics configurations for the specified bucket. ::

    aws s3api list-bucket-analytics-configurations \
        --bucket amzn-s3-demo-bucket

Output::

    {
        "AnalyticsConfigurationList": [
            {
                "StorageClassAnalysis": {},
                "Id": "1"
            }
        ],
        "IsTruncated": false
    }

For more information, see `Amazon S3 analytics - Storage Class Analysis <https://docs.aws.amazon.com/AmazonS3/latest/userguide/analytics-storage-class.html>`__ in the *Amazon S3 User Guide*.
