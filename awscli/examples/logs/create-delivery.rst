**To Create a delivery**

The following ``create-delivery`` example creates a delivery between a source and destination. ::

    aws logs create-delivery \
        --delivery-source-name demo-delivery-source \
        --delivery-destination-arn arn:aws:logs:us-east-1:123456789012:delivery-destination:demo-delivery-destination

Output::

    {
        "delivery": {
            "id": "Example1abcde2eCK",
            "arn": "arn:aws:logs:us-east-1:123456789012:delivery:Example1abcde2eCK",
            "deliverySourceName": "demo-delivery-source",
            "deliveryDestinationArn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:demo-delivery-destination",
            "deliveryDestinationType": "CWL",
            "recordFields": [
                "event_timestamp",
                "resource_id",
                "log_level",
                "event_message"
            ],
            "fieldDelimiter": ""
        }
    }

For more information, see `Enable logging from AWS services <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-and-resource-policy.html>`__ in the *Amazon CloudWatch Logs User Guide*.