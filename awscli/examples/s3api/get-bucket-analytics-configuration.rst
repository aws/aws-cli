**To retrieve the analytics configuration for a bucket**

The following ``get-bucket-analytics-configuration`` example retrieves the analytics configuration for the specified bucket. ::

    aws s3api get-bucket-analytics-configuration \
        --bucket my-bucket \
        --id 1

Output::

    {
        "AnalyticsConfiguration": {
            "StorageClassAnalysis": {},
            "Id": "1"
        }
    }
