**To Retrieve information about a logical delivery**

The following ``get-delivery`` example returns complete information about one logical delivery. ::

    aws logs get-delivery \
        --id Example1abcde2eCK 

Output::

    {
        "delivery": {
            "id": "Example1abcde2eCK",
            "arn": "arn:aws:logs:us-east-1:123456789012:delivery:Example1abcde2eCK",
            "deliverySourceName": "demo-delivery-source",
            "deliveryDestinationArn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:demo-delivery-destination",
            "deliveryDestinationType": "CWL"
        }
    }

For more information, see `Enable logging from AWS services <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-and-resource-policy.html>`__ in the *Amazon CloudWatch Logs User Guide*.