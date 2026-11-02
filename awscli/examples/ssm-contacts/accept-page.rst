**To accept a page during and engagement**

The following ``accept-page`` example uses an accept code sent to the contact channel to accept a page. ::

    aws ssm-contacts accept-page \
        --page-id "arn:aws:ssm-contacts:us-west-2:123456789012:page/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --accept-type READ \
        --accept-code 425440 

This command produces no output.

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.