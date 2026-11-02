**To update a contact channel**

The following ``update-contact-channel`` example updates the name and delivery address of a contact channel. ::

    aws ssm-contacts update-contact-channel \
        --contact-channel-id "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --name "akuas voice channel" \
        --delivery-address '{"SimpleAddress": "+15005550198"}'

This command produces no output.

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.