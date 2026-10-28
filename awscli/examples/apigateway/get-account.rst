**To get API Gateway account settings**

The following ``get-account`` example gets the API Gateway account settings. ::

    aws apigateway get-account

Output::

    {
        "cloudwatchRoleArn": "arn:aws:iam::123412341234:role/APIGatewayToCloudWatchLogsRole",
        "throttleSettings": {
            "rateLimit": 500.0,
            "burstLimit": 1000
        }
    }
