**To create a contact channel**

The following ``create-contact-channel`` example creates a contact channel of type SMS for the contact Akua Mansa. Contact channels can be created of type SMS, EMAIL, or VOICE. ::

    aws ssm-contacts create-contact-channel \
        --contact-id "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam" \
        --name "akuas sms-test" \
        --type SMS \
        --delivery-address '{"SimpleAddress": "+15005550199"}'

Output::

    {
        "ContactChannelArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.