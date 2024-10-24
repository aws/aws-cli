**To List the resource policies in this account**

The following ``describe-resource-policies`` example returns the resource policies in this account. ::

    aws logs describe-resource-policies

Output::

    {
        "resourcePolicies": [
            {
                "policyName": "DemoPolicy",
                "policyDocument": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"TrustEventsToStoreLogEvent\",\"Effect\":\"Allow\",\"Principal\":{\"Service\":[\"events.amazonaws.com\",\"delivery.logs.amazonaws.com\"]},\"Action\":[\"logs:CreateLogStream\",\"logs:PutLogEvents\"],\"Resource\":\"arn:aws:logs:us-east-2:123456789012:log-group:/*:*\"}]}",
                "lastUpdatedTime": 1711439903440
            },
            {
                "policyName": "ExamplePolicy",
                "policyDocument": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"Route53LogsToCloudWatchLogs\",\"Effect\":\"Allow\",\"Principal\":{\"Service\":[\"events.amazonaws.com\",\"delivery.logs.amazonaws.com\"]},\"Action\":[\"logs:PutLogEvents\",\"logs:CreateLogStream\"],\"Resource\":\"arn:aws:logs:us-east-2:123456789012:log-group:/aws/events/*:*\"}]}",
                "lastUpdatedTime": 1665917856059
            }
        ]
    }

For more information, see `Overview of managing access permissions to your CloudWatch Logs resources <Overview of managing access permissions to your CloudWatch Logs resources>`__ in the *Amazon CloudWatch Logs User Guide*.