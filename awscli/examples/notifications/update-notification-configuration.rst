**To update an existing notificationconfiguration**

The following ``update-notification-configuration`` example updates an existing NotificationConfiguration. ::

    aws notifications update-notification-configuration \
        --arn arn:aws:notifications::123456789012:configuration/a01jjzj251d2wxsss2wvtvxethb \
        --name cli-demo-notification \
        --description CLI-Demo-Notification \
        --aggregation-duration LONG

Output::

    {
        "arn": "arn:aws:notifications::123456789012:configuration/a01jjzj251d2wxsss2wvtvxethb"
    }

For more information, see `Editing notification configurations in AWS User Notifications <https://docs.aws.amazon.com/notifications/latest/userguide/edit-notifications.html>`__ in the *AWS User Notifications User Guide*.