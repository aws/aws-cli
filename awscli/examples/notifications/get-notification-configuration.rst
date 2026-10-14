**To view the details of a specified notificationconfiguration**

The following ``get-notification-configuration`` example displays the details about a specific NotificationConfiguration. ::

    aws notifications get-notification-configuration \
        --arn arn:aws:notifications::123456789012:configuration/a01jg2z8xtb12whwyg3ztxmjazh

Output::
    
    {
        "arn": "arn:aws:notifications::123456789012:configuration/a01jg2z8xtb12whwyg3ztxmjazh",
        "name": "Health-quick-setup",
        "description": "Health notifications created with quick setup",
        "status": "ACTIVE",
        "creationTime": "2024-10-27T02:31:34.987000+00:00",
        "aggregationDuration": "SHORT"
    }
