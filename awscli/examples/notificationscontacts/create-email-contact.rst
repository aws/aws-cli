**To create an email contact**

The following ``create-email-contact`` example creates an email contact for the provided email address. ::

    aws notificationscontacts create-email-contact \
        --name testuser \
        --email-address testuser@amazon.com

Output::

    {
        "arn": "arn:aws:notifications-contacts::123456789012:emailcontact/a01jjz84gswr5vvvc0ep0s8r7qr"
    }

For more information, see `Adding delivery channels in AWS User Notifications <https://docs.aws.amazon.com/notifications/latest/userguide/manage-delivery-channels.html>`__ in the *AWS User Notifications User Guide*.