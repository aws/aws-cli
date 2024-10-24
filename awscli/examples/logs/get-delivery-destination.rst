**To Retrieve information about a delivery destination**

The following ``get-delivery-destination`` example retrieves complete information about the delivery destination named ``demo-delivery-destination``. ::

    aws logs get-delivery-destination \
        --name demo-delivery-destination

Output::

    {
        "deliveryDestination": {
            "name": "demo-delivery-destination",
            "arn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:demo-delivery-destination",
            "deliveryDestinationType": "S3",
            "deliveryDestinationConfiguration": {
                "destinationResourceArn": "arn:aws:s3:::code-whisperer-s3-bucket-demo"
            }
        }
    }

For more information, see `Enable logging from AWS services <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-and-resource-policy.html>`__ in the *Amazon CloudWatch Logs User Guide*.