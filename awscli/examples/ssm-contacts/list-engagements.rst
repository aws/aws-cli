**To list all engagements**

The following ``list-engagements`` example lists engagements to escalation plans and contacts.  You can also list engagements for a single incident. ::

    aws ssm-contacts list-engagements

Output::

    {
        "Engagements": [
            {
                "EngagementArn": "arn:aws:ssm-contacts:us-west-2:123456789012:engagement/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "ContactArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam",
                "Sender": "cli",
                "StartTime": "2021-05-18T20:37:50.300000+00:00"
            },
            {
                "EngagementArn": "arn:aws:ssm-contacts:us-west-2:123456789012:engagement/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "ContactArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam",
                "Sender": "cli",
                "StartTime": "2021-05-18T18:40:26.666000+00:00"
            },
            {
                "EngagementArn": "arn:aws:ssm-contacts:us-west-2:123456789012:engagement/example_escalation/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "ContactArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/example_escalation",
                "Sender": "cli",
                "StartTime": "2021-05-18T18:25:41.151000+00:00"
            },
            {
                "EngagementArn": "arn:aws:ssm-contacts:us-west-2:123456789012:engagement/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "ContactArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam",
                "Sender": "cli",
                "StartTime": "2021-05-18T18:20:58.093000+00:00"
            }
        ]
    }

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.