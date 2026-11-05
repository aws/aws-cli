**To view the list of channels for a specific notificationconfiguration**

The following ``list-channels`` example displays the list of channels configured for a specific NotificationConfiguration. ::

    aws notifications list-channels \
        --notification-configuration-arn arn:aws:notifications::123456789012:configuration/a01jg38mtmd0ta5zshhstphfw8w
    
Output::
    
    {
        "channels": [
            "arn:aws:notifications-contacts::123456789012:emailcontact/a01jjz5n8e8557aswvm1fv4wqrf"
        ]
    }

For more information, see `Viewing delivery channel details in AWS User Notifications <https://docs.aws.amazon.com/notifications/latest/userguide/detail-delivery-channels.html>`__ in the *AWS User Notifications User Guide*.