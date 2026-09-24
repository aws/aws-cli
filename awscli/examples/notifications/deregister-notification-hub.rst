**To deregisters a notificationconfiguration**

The following ``deregister-notification-hub`` example deregisters a NotificationConfiguration in the specified Region. ::

    aws notifications deregister-notification-hub --notification-hub-region us-west-2

Output::

    {
        "notificationHubRegion": "us-west-2",
        "statusSummary": {
            "status": "DEREGISTERING",
            "reason": ""
        }
    }

For more information, see `Adding or removing a notification hub in AWS User Notifications <https://docs.aws.amazon.com/notifications/latest/userguide/nhr-add-remove.html>`__ in the *AWS User Notifications User Guide*.