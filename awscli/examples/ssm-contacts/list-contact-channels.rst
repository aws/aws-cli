**To list the contact channels of a contact**

The following ``list-contact-channels`` example lists the available contact channels of the specified contact. ::

    aws ssm-contacts list-contact-channels \
        --contact-id "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam"

Output::

    {
        "ContactChannels": [
            {
                "ContactChannelArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "ContactArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam",
                "Name": "akuas email",
                "Type": "EMAIL",
                "DeliveryAddress": {
                    "SimpleAddress": "akuam@example.com"
                },
                "ActivationStatus": "NOT_ACTIVATED"
            },
            {
                "ContactChannelArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "ContactArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam",
                "Name": "akuas sms",
                "Type": "SMS",
                "DeliveryAddress": {
                    "SimpleAddress": "+15005550100"
                },
                "ActivationStatus": "ACTIVATED"
            }
        ]
    }

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.