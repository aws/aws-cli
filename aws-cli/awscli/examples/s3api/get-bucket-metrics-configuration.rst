**To retrieve the metrics configuration for a bucket with a specific ID**

The following ``get-bucket-metrics-configuration`` example displays the metrics configuration for the specified bucket and ID. ::

    aws s3api get-bucket-metrics-configuration \
        --bucket amzn-s3-demo-bucket \
        --id 123

Output::

    {
        "MetricsConfiguration": {
            "Filter": {
                "Prefix": "logs"
            },
            "Id": "123"
        }
    }

For more information, see `CloudWatch metrics configurations <https://docs.aws.amazon.com/AmazonS3/latest/userguide/metrics-configurations.html>`__ in the *Amazon S3 User Guide*.
