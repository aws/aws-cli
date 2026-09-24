**To display details of an email contact**

The following ``get-email-contact`` example displays the details about the given notification email contact. ::

    aws notificationscontacts get-email-contact 
        --arn arn:aws:notifications-contacts::123456789012:emailcontact/a01jjz84gswr5vvvc0ep0s8r7qr

Output::

    {
        "emailContact": {
            "arn": "arn:aws:notifications-contacts::123456789012:emailcontact/a01jjz84gswr5vvvc0ep0s8r7qr",
            "name": "testuser",
            "address": "testuser@amazon.com",
            "status": "active",
            "creationTime": "2024-10-01T01:14:02.506000+00:00",
            "updateTime": "2024-10-01T01:14:02.506000+00:00"
        }
    }

For more information, see `Viewing delivery channel details in AWS User Notifications <https://docs.aws.amazon.com/notifications/latest/userguide/detail-delivery-channels.html>`__ in the *AWS User Notifications User Guide*.