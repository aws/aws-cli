**To list the details of a contact channel**

The following ``get-contact-channel`` example lists the details of a contact channel. ::

    aws ssm-contacts get-contact-channel \
        --contact-channel-id "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "ContactArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam",
        "ContactChannelArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Name": "akuas sms",
        "Type": "SMS",
        "DeliveryAddress": {
            "SimpleAddress": "+15005550199"
        },
        "ActivationStatus": "ACTIVATED"
    }

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.