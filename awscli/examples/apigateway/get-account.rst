**To get the API Gateway per-region account settings**

Command::

  aws apigateway get-account --region us-west-2

Output::

  {
      "cloudwatchRoleArn": "arn:aws:iam::123412341234:role/APIGatewayToCloudWatchLogsRole", 
      "throttleSettings": {
          "rateLimit": 500.0, 
          "burstLimit": 1000
      }
  }

