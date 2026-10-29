**To describe the details of an engagement**

The following ``describe-engagement`` example lists the details of an engagement to a contact or escalation plan. The subject and content are sent to the contact channels. ::

    aws ssm-contacts describe-engagement \
        --engagement-id "arn:aws:ssm-contacts:us-west-2:123456789012:engagement/example_escalation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "ContactArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/example_escalation",
        "EngagementArn": "arn:aws:ssm-contacts:us-west-2:123456789012:engagement/example_escalation/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Sender": "cli",
        "Subject": "cli-test",
        "Content": "Testing engagements via CLI",
        "PublicSubject": "cli-test",
        "PublicContent": "Testing engagements va CLI",
        "StartTime": "2021-05-18T18:25:41.151000+00:00"
    }

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.