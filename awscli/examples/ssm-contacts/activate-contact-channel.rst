**To activate a contact's contact channel**

The following ``activate-contact-channel`` example activates a contact channel and makes it usable as part of an incident. ::

    aws ssm-contacts activate-contact-channel \
        --contact-channel-id "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --activation-code "466136"

This command produces no output.

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.