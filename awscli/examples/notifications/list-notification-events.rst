**To view the list of notification events**

The following ``list-notification-events`` example displays the list of notification events. ::

    aws notifications list-notification-events 
    
Output::
    
    {
        "notificationEvents": [{
                "arn": "arn:aws:notifications:us-east-1:123456789012:configuration/a01jg2z8xtb12whwyg3ztxmjazh/event/a01jjta9p8wvpgt281q0e10e457",
                "notificationConfigurationArn": "arn:aws:notifications::123456789012:configuration/a01jg2z8xtb12whwyg3ztxmjazh",
                "relatedAccount": "123456789012",
                "creationTime": "2024-11-30T00:38:09.948000+00:00",
                "notificationEvent": {
                    "schemaVersion": "v1.0",
                    "sourceEventMetadata": {
                        "eventOriginRegion": "us-east-1",
                        "source": "aws.health",
                        "eventType": "AWS Health Event"
                    },
                    "messageComponents": {
                        "headline": "Health Event: AWS CLOUDFRONT OPERATIONAL ISSUE in global on account 123456789012."
                    },
                    "eventStatus": "null",
                    "notificationType": "ALERT"
                },
                "aggregationEventType": "NONE"
            },
            {
                "arn": "arn:aws:notifications:us-east-1:123456789012:configuration/a01jg2z8xtb12whwyg3ztxmjazh/event/a01jjt9mgqeewxcr08jccgxqnkj",
                "notificationConfigurationArn": "arn:aws:notifications::123456789012:configuration/a01jg2z8xtb12whwyg3ztxmjazh",
                "relatedAccount": "123456789012",
                "creationTime": "2024-11-30T00:26:36.142000+00:00",
                "notificationEvent": {
                    "schemaVersion": "v1.0",
                    "sourceEventMetadata": {
                        "eventOriginRegion": "us-east-1",
                        "source": "aws.health",
                        "eventType": "AWS Health Event"
                    },
                    "messageComponents": {
                        "headline": "Health Event: AWS CLOUDFRONT OPERATIONAL ISSUE in global on account 123456789012."
                    },
                    "eventStatus": "null",
                    "notificationType": "ALERT"
                },
                "aggregationEventType": "NONE"
            }
        ]
    }