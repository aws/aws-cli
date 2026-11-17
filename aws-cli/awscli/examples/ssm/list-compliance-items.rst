**Example 1: To list compliance items for a specific instance**

The following ``list-compliance-items`` example lists all compliance items for the specified instance. ::

    aws ssm list-compliance-items \
        --resource-ids "i-1234567890abcdef0" \
        --resource-types "ManagedInstance"

Output::

    {
        "ComplianceItems": [
            {
                "ComplianceType": "Association",
                "ResourceType": "ManagedInstance",
                "ResourceId": "i-1234567890abcdef0",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Title": "",
                "Status": "COMPLIANT",
                "Severity": "UNSPECIFIED",
                "ExecutionSummary": {
                    "ExecutionTime": 1550408470.0
                },
                "Details": {
                    "DocumentName": "AWS-GatherSoftwareInventory",
                    "DocumentVersion": "1"
                }
            },
            {
                "ComplianceType": "Association",
                "ResourceType": "ManagedInstance",
                "ResourceId": "i-1234567890abcdef0",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Title": "",
                "Status": "COMPLIANT",
                "Severity": "UNSPECIFIED",
                "ExecutionSummary": {
                    "ExecutionTime": 1550508475.0
                },
                "Details": {
                    "DocumentName": "AWS-UpdateSSMAgent",
                    "DocumentVersion": "1"
                }
        }
        ],
        "NextToken": "--token string truncated--"
    }

For more information, see `Learn details about Compliance <https://docs.aws.amazon.com/systems-manager/latest/userguide/compliance-about.html>`__ in the *AWS Systems Manager User Guide*.

**Example 2: To list compliance items for a specific instance and association ID**

The following ``list-compliance-items`` example lists all compliance items for the specified instance and association ID. ::

    aws ssm list-compliance-items \
        --resource-ids "i-1234567890abcdef0" \
        --resource-types "ManagedInstance" \
        --filters "Key=ComplianceType,Values=Association,Type=EQUAL" "Key=Id,Values=a1b2c3d4-5678-90ab-cdef-EXAMPLE22222,Type=EQUAL"

Output::

    {
        "ComplianceItems": [
            {
                "ComplianceType": "Association",
                "ResourceType": "ManagedInstance",
                "ResourceId": "i-1234567890abcdef0",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Title": "",
                "Status": "COMPLIANT",
                "Severity": "UNSPECIFIED",
                "ExecutionSummary": {
                    "ExecutionTime": 1550508475.0
                },
                "Details": {
                    "DocumentName": "AWS-UpdateSSMAgent",
                    "DocumentVersion": "1"
                }
            }
        ]
    }

For more information, see `Learn details about Compliance <https://docs.aws.amazon.com/systems-manager/latest/userguide/compliance-about.html>`__ in the *AWS Systems Manager User Guide*.

**Example 3: To list compliance items for an instance after a specific date and time**

The following ``list-compliance-items`` example lists all compliance items for an instance after the specified date and time. ::

    aws ssm list-compliance-items \
        --resource-ids "i-1234567890abcdef0" \
        --resource-types "ManagedInstance" \
        --filters "Key=ExecutionTime,Values=2019-02-18T16:00:00Z,Type=GREATER_THAN"

Output::

    {
        "ComplianceItems": [
            {
                "ComplianceType": "Association",
                "ResourceType": "ManagedInstance",
                "ResourceId": "i-1234567890abcdef0",
                "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Title": "",
                "Status": "COMPLIANT",
                "Severity": "UNSPECIFIED",
                "ExecutionSummary": {
                    "ExecutionTime": 1550508475.0
                },
                "Details": {
                    "DocumentName": "AWS-UpdateSSMAgent",
                    "DocumentVersion": "1"
                }
            }
        ]
    }

For more information, see `Learn details about Compliance <https://docs.aws.amazon.com/systems-manager/latest/userguide/compliance-about.html>`__ in the *AWS Systems Manager User Guide*.
