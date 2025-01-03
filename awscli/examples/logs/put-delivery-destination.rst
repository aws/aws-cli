**To Create or update a logical delivery destination**

The following ``put-delivery-destination`` example creates a logical delivery destination named ``demo-delivery-destination``. ::

    aws logs put-delivery-destination \
        --name demo-delivery-destination \
        "destinationResourceArn=arn:aws:s3:::code-whisperer-s3-bucket-demo"

Output::

    {
        "deliveryDestination": {
            "name": "demo-delivery-destination",
            "arn": "arn:aws:logs:us-east-1:123456789012:delivery-destination:demo-delivery-destination",
            "deliveryDestinationType": "S3",
            "deliveryDestinationConfiguration": {
                "destinationResourceArn": "arn:aws:s3:::doc-example-bucket"
            }
        }
    }

For more information, see `Enable logging from AWS services <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-and-resource-policy.html>`__ in the *Amazon CloudWatch Logs User Guide*.