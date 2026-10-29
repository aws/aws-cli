**To update the engagement plan of contact**

The following ``update-contact`` example updates the engagement plan of the contact Akua to include the three types of contacts channels. This is done after creating contact channels for Akua. ::

    aws ssm-contacts update-contact \
        --contact-id "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam" \
        --plan '{"Stages": [{"DurationInMinutes": 5, "Targets": [{"ChannelTargetInfo": {"ContactChannelId": "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111","RetryIntervalInMinutes": 1 }}]}, {"DurationInMinutes": 5, "Targets": [{"ChannelTargetInfo":{"ContactChannelId": "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222", "RetryIntervalInMinutes": 1}}]}, {"DurationInMinutes": 5, "Targets": [{"ChannelTargetInfo": {"ContactChannelId": "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333","RetryIntervalInMinutes": 1 }}]}]}'

This command produces no output.

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.