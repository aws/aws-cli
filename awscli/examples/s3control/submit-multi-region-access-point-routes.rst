**To update your Multi-Region Access Point routing configuration**

The following ``submit-multi-region-access-point-routes`` example updates the routing statuses of ``amzn-s3-demo-bucket1`` and ``amzn-s3-demo-bucket2`` in the ``us-west-2`` Region for your Multi-Region Access Point. ::

    aws s3control submit-multi-region-access-point-routes \
        --region us-west-2 \
        --account-id 123456789012 \
        --mrap MultiRegionAccessPoint_ARN \
        --route-updates Bucket=amzn-s3-demo-bucket1,TrafficDialPercentage=100 Bucket=amzn-s3-demo-bucket2,TrafficDialPercentage=0

This command produces no output.

For more information, see `Using Amazon S3 Multi-Region Access Point failover controls <https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingFailover.html>`__ in the *Amazon S3 User Guide*.
