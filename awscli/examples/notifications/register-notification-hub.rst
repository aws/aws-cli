**To registers a notificationconfiguration**

The following ``register-notification-hub`` example registers a Notification hub. ::

    aws notifications register-notification-hub --notification-hub-region us-west-2

Output::

    {
        "notificationHubRegion": "us-west-2",
        "statusSummary": {
            "status": "REGISTERING",
            "reason": ""
        },
        "creationTime": "2024-11-01T03:02:58.561000+00:00"
    }

For more information, see `Adding or removing a notification hub in AWS User Notifications <https://docs.aws.amazon.com/notifications/latest/userguide/nhr-add-remove.html>`__ in the *AWS User Notifications User Guide*.