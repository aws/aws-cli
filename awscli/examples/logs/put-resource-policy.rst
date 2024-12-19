**To Create or update a resource policy**

The following ``put-resource-policy`` example creates a resource policy allowing EventBridge service to put log events to this account. ::

    aws logs put-resource-policy \
        --policy-name AllowEventBridgeEventsToCWLogs \
        --policy-document file://policy.json

The file ``policy.json`` is a JSON document in the current folder.

    {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "TrustEventsToStoreLogEvent",
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "events.amazonaws.com",
                    "delivery.logs.amazonaws.com"
                ]
            }
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:us-east-1:123456789012:log-group:/aws/events/*:*"
        }]
    }

Output::

    {
        "resourcePolicy": {
            "policyName": "AllowEventBridgeEventsToCWLogs",
            "policyDocument": "{\n\"Version\": \"2012-10-17\",\n\"Statement\": [{\n\"Sid\": \"TrustEventsToStoreLogEvent\",\n\"Effect\": \"Allow\",\n\"Principal\": {\n\"Service\": [\"events.amazonaws.com\", \"delivery.logs.amazonaws.com\"]\n},\n\"Action\": [\"logs:CreateLogStream\", \"logs:PutLogEvents\"],\n\"Resource\": \"arn:aws:logs:us-east-1:123456789012:log-group:/aws/events/*:*\"\n}]\n}\n",
            "lastUpdatedTime": 1724943159296
        }
    }

For more information, see `Overview of managing access permissions to your CloudWatch Logs resources <Overview of managing access permissions to your CloudWatch Logs resources>`__ in the *Amazon CloudWatch Logs User Guide*.