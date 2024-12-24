**To Retrieve a list of the deliveries**

The following ``describe-deliveries`` example retrieves a list of the deliveries that have been created in the account. ::

    aws logs describe-deliveries

Output::

    {
        "deliveries": [
            {
                "id": "Example2abcde3eCK",
                "arn": "arn:aws:logs:us-east-1:123456789012:delivery:Example2abcde3eCK",
                "deliverySourceName": "demo-delivery-source",
                "deliveryDestinationArn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:demo-delivery-destination"
            },
            {
                "id": "Example1abcde2eCK",
                "arn": "arn:aws:logs:us-east-1:123456789012:delivery:Example1abcde2eCK",
                "deliverySourceName": "example-delivery-source",
                "deliveryDestinationArn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:example-delivery-destination"
            }
        ]
    }

For more information, see `Enable logging from AWS services <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-and-resource-policy.html>`__ in the *Amazon CloudWatch Logs User Guide*.