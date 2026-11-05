**Example 1: To retrieve a list of all access points for an account**

The following ``list-access-points`` example displays a list of all access points attached to buckets owned by account 123456789012. ::

    aws s3control list-access-points \
        --account-id 123456789012

Output::

    {
        "AccessPointList": [
            {
                "Name": "finance-ap",
                "NetworkOrigin": "Internet",
                "Bucket": "amzn-s3-demo-bucket1"
            },
            {
                "Name": "managers-ap",
                "NetworkOrigin": "Internet",
                "Bucket": "amzn-s3-demo-bucket1"
            },
            {
                "Name": "private-network-ap",
                "NetworkOrigin": "VPC",
                "VpcConfiguration": {
                    "VpcId": "1a2b3c"
                },
                "Bucket": "amzn-s3-demo-bucket1"
            },
            {
                "Name": "customer-ap",
                "NetworkOrigin": "Internet",
                "Bucket": "amzn-s3-demo-bucket2"
            },
            {
                "Name": "public-ap",
                "NetworkOrigin": "Internet",
                "Bucket": "amzn-s3-demo-bucket2"
            }
        ]
    }

**Example 2: To retrieve a list of all access points for a bucket**

The following ``list-access-points`` example retrieves a list of all access points attached to the bucket ``amzn-s3-demo-bucket2`` owned by account 123456789012. ::

    aws s3control list-access-points \
        --account-id 123456789012 \
        --bucket amzn-s3-demo-bucket2

Output::

    {
        "AccessPointList": [
            {
                "Name": "customer-ap",
                "NetworkOrigin": "Internet",
                "Bucket": "amzn-s3-demo-bucket2"
            },
            {
                "Name": "public-ap",
                "NetworkOrigin": "Internet",
                "Bucket": "amzn-s3-demo-bucket2"
            }
        ]
    }

For more information, see `Managing Data Access with Amazon S3 Access Points <https://docs.aws.amazon.com/AmazonS3/latest/dev/access-points.html>`__ in the *Amazon Simple Storage Service Developer Guide*.
