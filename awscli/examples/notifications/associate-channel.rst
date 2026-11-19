**To associate a delivery channel**

The following ``associate-channel`` example associates a delivery channel with a particular NotificationConfiguration. ::

    aws notifications associate-channel \
        --arn arn:aws:notifications-contacts::123456789012:emailcontact/a01jjz5n8e8557aswvm1fv4wqrf \
        --notification-configuration-arn arn:aws:notifications::123456789012:configuration/a01jjzj251d2wxsss2wvtvxethb

This command produces no output.

For more information, see `Adding delivery channels in AWS User Notifications <https://docs.aws.amazon.com/notifications/latest/userguide/manage-delivery-channels.html>`__ in the *AWS User Notifications User Guide*.