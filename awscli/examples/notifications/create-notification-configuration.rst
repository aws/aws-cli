**To create a notificationconfiguration**

The following ``create-notification-configuration`` example creates a NotificationConfiguration. ::

    aws notifications create-notification-configuration \
        --name testnotification-1 \
        --aggregation-duration SHORT \
        --description CLI-Demo
        
Output::

    {
        "arn": "arn:aws:notifications::123456789012:configuration/a01jjzj251d2wxsss2wvtvxethb",
        "status": "INACTIVE"
    }

For more information, see `Adding delivery channels in AWS User Notifications <https://docs.aws.amazon.com/notifications/latest/userguide/manage-delivery-channels.html>`__ in the *AWS User Notifications User Guide*.