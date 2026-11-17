**To get API Gateway account settings**

The following ``get-account`` example gets the API Gateway account settings. ::

    aws apigateway get-account

Output::

    {
        "cloudwatchRoleArn": "arn:aws:iam::123456789012:role/APIGatewayToCloudWatchLogsRole",
        "throttleSettings": {
            "rateLimit": 500.0,
            "burstLimit": 1000
        }
    }

For more information, see `Set up CloudWatch logging for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-logging.html>`__ in the *Amazon API Gateway Developer Guide*.
