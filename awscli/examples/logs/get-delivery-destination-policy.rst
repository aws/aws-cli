**To Retrieve delivery destination policy**

The following ``get-delivery-destination`` example retrieves the policy for the delivery destination named ``demo-delivery-destination``. ::

    aws logs get-delivery-destination-policy \
        --delivery-destination-name demo-delivery-destination

Output::

    {
        "policy": {
            "deliveryDestinationPolicy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"AllowLogDeliveryActions\",\"Effect\":\"Allow\",\"Principal\":{\"AWS\":\"arn:aws:iam::123456789012:root\"},\"Action\":\"logs:CreateDelivery\",\"Resource\":[\"arn:aws:logs:us-east-1:123456789012:delivery-source:*\",\"arn:aws:logs:us-east-1:123456789012:delivery:*\",\"arn:aws:logs:us-east-1:123456789012:delivery-destination:*\"]}]}"
        }
    }

For more information, see `Enable logging from AWS services <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/AWS-logs-and-resource-policy.html>`__ in the *Amazon CloudWatch Logs User Guide*.