**Example 1: To describe a contact plan**

The following ``get-contact`` example describes a contact. ::

    aws ssm-contacts get-contact \
        --contact-id "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam"

Output::

    {
        "ContactArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam",
        "Alias": "akuam",
        "DisplayName": "Akua Mansa",
        "Type": "PERSONAL",
        "Plan": {
            "Stages": [
                {
                    "DurationInMinutes": 5,
                    "Targets": [
                        {
                            "ChannelTargetInfo": {
                                "ContactChannelId": "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                                "RetryIntervalInMinutes": 1
                            }
                        }
                    ]
                },
                {
                    "DurationInMinutes": 5,
                    "Targets": [
                        {
                            "ChannelTargetInfo": {
                                "ContactChannelId": "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                                "RetryIntervalInMinutes": 1
                            }
                        }
                    ]
                },
                {
                    "DurationInMinutes": 5,
                    "Targets": [
                        {
                            "ChannelTargetInfo": {
                                "ContactChannelId": "arn:aws:ssm-contacts:us-west-2:123456789012:contact-channel/akuam/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                                "RetryIntervalInMinutes": 1
                            }
                        }
                    ]
                }
            ]
        }
    }

**Example 2: To describe an escalation plan**

The following ``get-contact`` example describes an escalation plan. ::

    aws ssm-contacts get-contact \
        --contact-id "arn:aws:ssm-contacts:us-west-2:123456789012:contact/example_escalation"

Output::

    {
        "ContactArn": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/example_escalation",
        "Alias": "example_escalation",
        "DisplayName": "Example Escalation",
        "Type": "ESCALATION",
        "Plan": {
            "Stages": [
                {
                    "DurationInMinutes": 5,
                    "Targets": [
                        {
                            "ContactTargetInfo": {
                                "ContactId": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/akuam",
                                "IsEssential": true
                            }
                        }
                    ]
                },
                {
                    "DurationInMinutes": 5,
                    "Targets": [
                        {
                            "ContactTargetInfo": {
                                "ContactId": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/alejr",
                                "IsEssential": false
                            }
                        }
                    ]
                },
                {
                    "DurationInMinutes": 0,
                    "Targets": [
                        {
                            "ContactTargetInfo": {
                                "ContactId": "arn:aws:ssm-contacts:us-west-2:123456789012:contact/anasi",
                                "IsEssential": false
                            }
                        }
                    ]
                }
            ]
        }
    }

For more information, see `Contacts <https://docs.aws.amazon.com/incident-manager/latest/userguide/contacts.html>`__ in the *Incident Manager User Guide*.