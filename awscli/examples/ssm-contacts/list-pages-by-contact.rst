**To list pages by contact**

The following ``list-pages-by-contact`` example lists all pages to the specified contact. ::

    aws ssm-contacts list-pages-by-contact \
        --contact-id "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam"

Output::

    {
        "Pages": [
            {
                "PageArn": "arn:aws:ssm-contacts:us-west-2:123456789012:page/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "EngagementArn": "arn:aws:ssm-contacts:us-west-2:123456789012:engagement/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "ContactArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam",
                "Sender": "cli",
                "SentTime": "2021-05-18T18:43:29.301000+00:00",
                "DeliveryTime": "2021-05-18T18:43:55.265000+00:00",
                "ReadTime": "2021-05-18T18:43:55.708000+00:00"
            }
        ]
    }

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.