**To delete a contact channel**

The following ``delete-contact-channel`` example deletes a contact channel. Deleting a contact channel ensures the contact channel will not be paged during an incident. ::

    aws ssm-contacts delete-contact-channel \
        --contact-channel-id "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

This command produces no output.

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.