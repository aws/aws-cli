**To display the list of all email contact**

The following ``list-email-contacts`` example displays the list of all notification email contacts created in an account. ::

    aws notificationscontacts list-email-contacts

Output::

    {
        "emailContacts": [
            {
                "arn": "arn:aws:notifications-contacts::123456789012:emailcontact/a01jjz50jvqx2xndxhnyd8cptg1",
                "name": "testuser01",
                "address": "testuser01+1@amazon.com",
                "status": "inactive",
                "creationTime": "2024-09-30T21:42:00.823000+00:00",
                "updateTime": "2024-09-30T21:42:00.823000+00:00"
            },
            {
                "arn": "arn:aws:notifications-contacts::123456789012:emailcontact/a01jjz84gswr5vvvc0ep0s8r7qr",
                "name": "testuser",
                "address": "testuser@amazon.com",
                "status": "active",
                "creationTime": "2024-10-01T01:14:02.506000+00:00",
                "updateTime": "2024-10-01T01:14:02.506000+00:00"
            }
        ]
    }

For more information, see `Viewing delivery channel details in AWS User Notifications <https://docs.aws.amazon.com/notifications/latest/userguide/detail-delivery-channels.html>`__ in the *AWS User Notifications User Guide*.