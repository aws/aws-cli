**To Retrieve a list of the delivery destinations**

The following ``describe-delivery-destinations`` example retrieves a list of delivery destinations that have been created in the account. ::

    aws logs describe-delivery-destinations

Output::

    {
        "deliveryDestinations": [
            {
                "name": "KinesisFirehose",
                "arn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:KinesisFirehose",
                "deliveryDestinationType": "FH",
                "deliveryDestinationConfiguration": {
                    "destinationResourceArn": "arn:aws:firehose:us-east-1:123456789012:deliverystream/PUT-S3-Tlha6"
                }
            },
            {
                "name": "demo-delivery-destination",
                "arn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:demo-delivery-destination",
                "deliveryDestinationType": "CWL",
                "deliveryDestinationConfiguration": {
                    "destinationResourceArn": "arn:aws:logs:us-east-1:123456789012:log-group:code-whisperer-logs:*"
                }
            },
            {
                "name": "example-delivery-destination",
                "arn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:example-delivery-destination",
                "deliveryDestinationType": "S3",
                "deliveryDestinationConfiguration": {
                    "destinationResourceArn": "arn:aws:s3:::code-whisperer-s3-bucket-test"
                }
            }
        ]
    }

For more information, see `Enable logging from AWS services <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-and-resource-policy.html>`__ in the *Amazon CloudWatch Logs User Guide*.