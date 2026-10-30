**To list pages to contact channels started from an engagement.**

The following ``list-pages-by-engagement`` example lists the pages that occurred while engaging the defined engagement plan. ::

    aws ssm-contacts list-pages-by-engagement \
        --engagement-id "arn:aws:ssm-contacts:us-west-2:123456789012:engagement/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "Pages": [
            {
                "PageArn": "arn:aws:ssm-contacts:us-west-2:123456789012:page/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "EngagementArn": "arn:aws:ssm-contacts:us-west-2:123456789012:engagement/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "ContactArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam",
                "Sender": "cli",
                "SentTime": "2021-05-18T18:40:27.245000+00:00"
            }
        ]
    }

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.