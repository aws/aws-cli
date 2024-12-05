**To Retrieve information about a delivery source**

The following ``get-delivery-source`` example retrieves complete information about the delivery source named ``demo-delivery-source``. ::

    aws logs get-delivery-source \
        --name demo-delivery-source

Output::

    {
        "deliverySource": {
            "name": "demo-delivery-source",
            "arn": "arn:aws:logs:us-east-1:123456789012:delivery-source:demo-delivery-source",
            "resourceArns": [
                "arn:aws:codewhisperer:us-east-1:123456789012:customization/ABC1DE2FGHI"
            ],
            "service": "codewhisperer",
            "logType": "EVENT_LOGS"
        }
    }

For more information, see `Enable logging from AWS services <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-and-resource-policy.html>`__ in the *Amazon CloudWatch Logs User Guide*.