**Example 1: To page a contact's contact channels**

The following ``start-engagement`` example pages a contact's contact channels. Sender, subject, public-subject, and public-content are all free from fields. Incident Manager sends the subject and content to the provided VOICE or EMAIL contact channels. Incident Manager sends the public-subject and public-content to the provided SMS contact channels. Sender is used to track who started the engagement. ::

    aws ssm-contacts start-engagement \
        --contact-id  "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam" \
        --sender "cli" \
        --subject "cli-test" \
        --content "Testing engagements via CLI" \
        --public-subject "cli-test" \
        --public-content "Testing engagements va CLI"

Output::

    {
        "EngagementArn": "arn:aws:ssm-contacts:us-west-2:123456789012:engagement/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.

**Example 2: To page a contact in the provided escalation plan.**

The following ``start-engagement`` example engages contacts through an escalation plan. Each contact is paged according to their engagement plan. ::

    aws ssm-contacts start-engagement \
        --contact-id  "arn:aws:ssm-contacts:us-west-2:123456789012:contact/example_escalation" \
        --sender "cli" \
        --subject "cli-test" \
        --content "Testing engagements via CLI" \
        --public-subject "cli-test" \
        --public-content "Testing engagements va CLI"

Output::

    {
        "EngagementArn": "arn:aws:ssm-contacts:us-west-2:123456789012:engagement/example_escalation/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.