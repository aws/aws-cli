**To view the details of a specified eventrule**

The following ``get-event-rule`` example display the details about a specific EventRule. ::

    aws notifications get-event-rule \
        --arn arn:aws:notifications::123456789012:configuration/a01jg2z8xtb12whwyg3ztxmjazh/rule/a01jg2z8ydvea0x0v3z8xkwjrrs
    
Output::
    
    {
        "arn": "arn:aws:notifications::123456789012:configuration/a01jg2z8xtb12whwyg3ztxmjazh/rule/a01jg2z8ydvea0x0v3z8xkwjrrs",
        "notificationConfigurationArn": "arn:aws:notifications::123456789012:configuration/a01jg2z8xtb12whwyg3ztxmjazh",
        "creationTime": "2024-10-27T02:31:35.611000+00:00",
        "source": "aws.health",
        "eventType": "AWS Health Event",
        "eventPattern": "",
        "regions": [
            "us-east-1"
        ],
        "managedRules": [
            "arn:aws:events:us-east-1:123456789012:rule/AWSUserNotificationsManagedRule-aa1apyq"
        ],
        "statusSummaryByRegion": {
            "us-east-1": {
                "status": "ACTIVE",
                "reason": ""
            }
        }
    }
