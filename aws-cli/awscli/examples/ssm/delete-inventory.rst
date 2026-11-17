**Example 1: To delete a custom inventory type**

The following ``delete-inventory`` example deletes a custom inventory schema. ::

    aws ssm delete-inventory \
        --type-name "Custom:RackInfo" \
        --schema-delete-option "DeleteSchema"

Output::

    {
        "DeletionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "TypeName": "Custom:RackInfo",
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
        }
    }

For more information, see `Working with custom inventory <https://docs.aws.amazon.com/systems-manager/latest/userguide/inventory-custom.html>`__ in the *AWS Systems Manager User Guide*.

**Example 2: To disable a custom inventory type**

The following ``delete-inventory`` example disables a custom inventory schema. ::

    aws ssm delete-inventory \
        --type-name "Custom:RackInfo" \
        --schema-delete-option "DisableSchema"

Output::

    {
        "DeletionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "TypeName": "Custom:RackInformation",
        "DeletionSummary": {
            "TotalCount": 0,
            "RemainingCount": 0,
            "SummaryItems": []
        }
    }

For more information, see `Working with custom inventory <https://docs.aws.amazon.com/systems-manager/latest/userguide/inventory-custom.html>`__ in the *AWS Systems Manager User Guide*.
