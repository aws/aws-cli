**To list the details of a page to a contact channel**

The following ``describe-page`` example lists details of a page to a contact channel. The page will include the subject and content provided. ::

    aws ssm-contacts describe-page \
        --page-id "arn:aws:ssm-contacts:us-west-2:123456789012:page/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "PageArn": "arn:aws:ssm-contacts:us-west-2:123456789012:page/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "EngagementArn": "arn:aws:ssm-contacts:us-west-2:123456789012:engagement/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "ContactArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam",
        "Sender": "cli",
        "Subject": "cli-test",
        "Content": "Testing engagements via CLI",
        "PublicSubject": "cli-test",
        "PublicContent": "Testing engagements va CLI",
        "SentTime": "2021-05-18T18:43:29.301000+00:00",
        "ReadTime": "2021-05-18T18:43:55.708000+00:00",
        "DeliveryTime": "2021-05-18T18:43:55.265000+00:00"
    }

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.