**Example 1: To get inventory deletions**

The following ``describe-inventory-deletions`` example retrieves details for inventory deletion operations. ::

    aws ssm describe-inventory-deletions

Output::

    {
        "InventoryDeletions": [
            {
                "DeletionId": "6961492a-8163-44ec-aa1e-01234567850",
                "TypeName": "Custom:RackInformation",
                "DeletionStartTime": 1550254911.0,
                "LastStatus": "InProgress",
                "LastStatusMessage": "The Delete is in progress",
                "DeletionSummary": {
                    "TotalCount": 0,
                    "RemainingCount": 0,
                    "SummaryItems": []
                },
                "LastStatusUpdateTime": 1550254911.0
            },
            {
                "DeletionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "TypeName": "Custom:RackInfo",
                "DeletionStartTime": 1550254859.0,
                "LastStatus": "InProgress",
                "LastStatusMessage": "The Delete is in progress",
                "DeletionSummary": {
                    "TotalCount": 1,
                    "RemainingCount": 1,
                    "SummaryItems": [
                        {
                            "Version": "1.0",
                            "Count": 1,
                            "RemainingCount": 1
                        }
                    ]
                },
                "LastStatusUpdateTime": 1550254859.0
            }
        ]
    }

For more information, see `Working with custom inventory <https://docs.aws.amazon.com/systems-manager/latest/userguide/inventory-custom.html>`__ in the *AWS Systems Manager User Guide*.

**Example 2: To get details of a specific inventory deletion**

The following ``describe-inventory-deletions`` example retrieves details for a specific inventory deletion operation. ::

    aws ssm describe-inventory-deletions \
        --deletion-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "InventoryDeletions": [
            {
                "DeletionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "TypeName": "Custom:RackInfo",
                "DeletionStartTime": 1550254859.0,
                "LastStatus": "InProgress",
                "LastStatusMessage": "The Delete is in progress",
                "DeletionSummary": {
                    "TotalCount": 1,
                    "RemainingCount": 1,
                    "SummaryItems": [
                        {
                            "Version": "1.0",
                            "Count": 1,
                            "RemainingCount": 1
                        }
                    ]
                },
                "LastStatusUpdateTime": 1550254859.0
            }
        ]
    }

For more information, see `Working with custom inventory <https://docs.aws.amazon.com/systems-manager/latest/userguide/inventory-custom.html>`__ in the *AWS Systems Manager User Guide*.
