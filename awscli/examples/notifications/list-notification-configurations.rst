**To view the list of notificationconfiguration **

The following ``list-notification-configurations`` example displays the list of NotificationConfiguration. ::

    aws notifications list-notification-configurations
    
Output::
    
    {
        "notificationConfigurations": [
            {
                "arn": "arn:aws:notifications::123456789012:configuration/a01jg38mtmd0ta5zshhstphfw8w",
                "name": "EC2-quick-setup",
                "description": "EC2 notifications created with quick setup",
                "status": "ACTIVE",
                "creationTime": "2024-10-27T05:15:22.126000+00:00",
                "aggregationDuration": "SHORT"
            },
            {
                "arn": "arn:aws:notifications::123456789012:configuration/a01jg2z8xtb12whwyg3ztxmjazh",
                "name": "Health-quick-setup",
                "description": "Health notifications created with quick setup",
                "status": "ACTIVE",
                "creationTime": "2024-10-27T02:31:34.987000+00:00",
                "aggregationDuration": "SHORT"
            },
            {
                "arn": "arn:aws:notifications::123456789012:configuration/a01jg2ne1shtc7pbwanwdvn0h7t",
                "name": "test-notification",
                "description": "test-notification",
                "status": "INACTIVE",
                "creationTime": "2024-10-26T23:39:37.137000+00:00",
                "aggregationDuration": "SHORT"
            }
        ]
    }