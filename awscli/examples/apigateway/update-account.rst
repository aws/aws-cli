**To change the IAM Role ARN for logging to CloudWatch Logs**

The following ``update-account`` example changes the IAM Role ARN for logging to CloudWatch Logs. ::

    aws apigateway update-account --patch-operations op='replace',path='/cloudwatchRoleArn',value='arn:aws:iam::123412341234:role/APIGatewayToCloudWatchLogs'

Output::

    {
        "cloudwatchRoleArn": "arn:aws:iam::123412341234:role/APIGatewayToCloudWatchLogs",
        "throttleSettings": {
            "rateLimit": 1000.0,
            "burstLimit": 2000
        }
    }
