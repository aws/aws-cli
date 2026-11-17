**Example 1: To list compliance summaries for all compliance types**

The following ``list-compliance-summaries`` example lists compliance summaries for all compliance types in your account. ::

    aws ssm list-compliance-summaries

Output::

    {
        "ComplianceSummaryItems": [
            {
                "ComplianceType": "Association",
                "CompliantSummary": {
                    "CompliantCount": 2,
                    "SeveritySummary": {
                        "CriticalCount": 0,
                        "HighCount": 0,
                        "MediumCount": 0,
                        "LowCount": 0,
                        "InformationalCount": 0,
                        "UnspecifiedCount": 2
                    }
                },
                "NonCompliantSummary": {
                    "NonCompliantCount": 0,
                    "SeveritySummary": {
                        "CriticalCount": 0,
                        "HighCount": 0,
                        "MediumCount": 0,
                        "LowCount": 0,
                        "InformationalCount": 0,
                        "UnspecifiedCount": 0
                    }
                }
            },
            {
                "ComplianceType": "Patch",
                "CompliantSummary": {
                    "CompliantCount": 1,
                    "SeveritySummary": {
                        "CriticalCount": 0,
                        "HighCount": 0,
                        "MediumCount": 0,
                        "LowCount": 0,
                        "InformationalCount": 0,
                        "UnspecifiedCount": 1
                    }
                },
                "NonCompliantSummary": {
                    "NonCompliantCount": 1,
                    "SeveritySummary": {
                        "CriticalCount": 1,
                        "HighCount": 0,
                        "MediumCount": 0,
                        "LowCount": 0,
                        "InformationalCount": 0,
                        "UnspecifiedCount": 0
                    }
                }
        }
        ],
        "NextToken": "eyJOZXh0VG9rZW4iOiBudWxsLCAiYm90b190cnVuY2F0ZV9hbW91bnQiOiAyfQ=="
    }

For more information, see `Learn details about Compliance <https://docs.aws.amazon.com/systems-manager/latest/userguide/compliance-about.html>`__ in the *AWS Systems Manager User Guide*.

**Example 2: To list compliance summaries for a specific compliance type**

The following ``list-compliance-summaries`` example lists the compliance summary for the Patch compliance type. ::

    aws ssm list-compliance-summaries \
        --filters "Key=ComplianceType,Values=Patch,Type=EQUAL"

Output::

    {
        "ComplianceSummaryItems": [
            {
                "ComplianceType": "Patch",
                "CompliantSummary": {
                    "CompliantCount": 1,
                    "SeveritySummary": {
                        "CriticalCount": 0,
                        "HighCount": 0,
                        "MediumCount": 0,
                        "LowCount": 0,
                        "InformationalCount": 0,
                        "UnspecifiedCount": 1
                    }
                },
                "NonCompliantSummary": {
                    "NonCompliantCount": 1,
                    "SeveritySummary": {
                        "CriticalCount": 1,
                        "HighCount": 0,
                        "MediumCount": 0,
                        "LowCount": 0,
                        "InformationalCount": 0,
                        "UnspecifiedCount": 0
                    }
                }
            }
        ]
    }

For more information, see `Learn details about Compliance <https://docs.aws.amazon.com/systems-manager/latest/userguide/compliance-about.html>`__ in the *AWS Systems Manager User Guide*.
