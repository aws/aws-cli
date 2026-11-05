**Example 1: To list resource-level compliance summary counts**

The following ``list-resource-compliance-summaries`` example lists resource-level compliance summary counts. ::

    aws ssm list-resource-compliance-summaries

Output::

    {
        "ResourceComplianceSummaryItems": [
            {
                "ComplianceType": "Association",
                "ResourceType": "ManagedInstance",
                "ResourceId": "i-1234567890abcdef0",
                "Status": "COMPLIANT",
                "OverallSeverity": "UNSPECIFIED",
                "ExecutionSummary": {
                    "ExecutionTime": 1550509273.0
                },
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
                "ResourceType": "ManagedInstance",
                "ResourceId": "i-9876543210abcdef0",
                "Status": "COMPLIANT",
                "OverallSeverity": "UNSPECIFIED",
                "ExecutionSummary": {
                    "ExecutionTime": 1550248550.0,
                    "ExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                    "ExecutionType": "Command"
                },
                "CompliantSummary": {
                    "CompliantCount": 397,
                    "SeveritySummary": {
                        "CriticalCount": 0,
                        "HighCount": 0,
                        "MediumCount": 0,
                        "LowCount": 0,
                        "InformationalCount": 0,
                        "UnspecifiedCount": 397
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
            }
        ],
        "NextToken": "--token string truncated--"
    }

For more information, see `Learn details about Compliance <https://docs.aws.amazon.com/systems-manager/latest/userguide/compliance-about.html>`__ in the *AWS Systems Manager User Guide*.

**Example 2: To list resource-level compliance summaries for a specific compliance type**

The following ``list-resource-compliance-summaries`` example lists resource-level compliance summaries for the Patch compliance type. ::

    aws ssm list-resource-compliance-summaries \
        --filters "Key=ComplianceType,Values=Patch,Type=EQUAL"

Output::

    {
        "ResourceComplianceSummaryItems": [
            {
                "ComplianceType": "Patch",
                "ResourceType": "ManagedInstance",
                "ResourceId": "i-9876543210abcdef0",
                "Status": "COMPLIANT",
                "OverallSeverity": "UNSPECIFIED",
                "ExecutionSummary": {
                    "ExecutionTime": 1550248550.0,
                    "ExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                    "ExecutionType": "Command"
                },
                "CompliantSummary": {
                    "CompliantCount": 397,
                    "SeveritySummary": {
                        "CriticalCount": 0,
                        "HighCount": 0,
                        "MediumCount": 0,
                        "LowCount": 0,
                        "InformationalCount": 0,
                        "UnspecifiedCount": 397
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
            }
        ]
    }

For more information, see `Learn details about Compliance <https://docs.aws.amazon.com/systems-manager/latest/userguide/compliance-about.html>`__ in the *AWS Systems Manager User Guide*.
