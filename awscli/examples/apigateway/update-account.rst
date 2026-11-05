**To change the IAM Role ARN for logging to CloudWatch Logs**

The following ``update-account`` example changes the IAM Role ARN for logging to CloudWatch Logs. ::

    aws apigateway update-account \
        --patch-operations op='replace',path='/cloudwatchRoleArn',value='arn:aws:iam::123456789012:role/APIGatewayToCloudWatchLogs'

Output::

    {
        "cloudwatchRoleArn": "arn:aws:iam::123456789012:role/APIGatewayToCloudWatchLogs",
        "throttleSettings": {
            "rateLimit": 1000.0,
            "burstLimit": 2000
        }
    }

For more information, see `Set up CloudWatch logging for REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-logging.html>`__ in the *Amazon API Gateway Developer Guide*.
