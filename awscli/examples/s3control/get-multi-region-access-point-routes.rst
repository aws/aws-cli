**To query the current Multi-Region Access Point route configuration**

The following ``get-multi-region-access-point-routes`` example returns the current routing configuration for the specified Multi-Region Access Point. ::

    aws s3control get-multi-region-access-point-routes \
        --region Region \
        --account-id 123456789012 \
        --mrap MultiRegionAccessPoint_ARN

Output::

    {
        "Mrap": "arn:aws:s3::123456789012:accesspoint/0000000000000.mrap",
        "Routes": [
            {
                "Bucket": "amzn-s3-demo-bucket1",
                "Region": "ap-southeast-2",
                "TrafficDialPercentage": 100
            },
            {
                "Bucket": "amzn-s3-demo-bucket2",
                "Region": "us-west-1",
                "TrafficDialPercentage": 0
            }
        ]
    }

For more information, see `Using Amazon S3 Multi-Region Access Point failover controls <https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingFailover.html>`__ in the *Amazon S3 User Guide*.
