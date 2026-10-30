**Example 1: To list all targets for a Maintenance Window**

The following ``describe-maintenance-window-targets`` example lists all of the targets for a maintenance window. ::

    aws ssm describe-maintenance-window-targets \
        --window-id "mw-06cf17cbefEXAMPLE"

Output::

    {
        "Targets": [
            {
                "ResourceType": "INSTANCE",
                "OwnerInformation": "Single instance",
                "WindowId": "mw-06cf17cbefEXAMPLE",
                "Targets": [
                    {
                        "Values": [
                            "i-0000293ffdEXAMPLE"
                        ],
                        "Key": "InstanceIds"
                    }
                ],
                "WindowTargetId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            {
                "ResourceType": "INSTANCE",
                "OwnerInformation": "Two instances in a list",
                "WindowId": "mw-06cf17cbefEXAMPLE",
                "Targets": [
                    {
                        "Values": [
                            "i-0000293ffdEXAMPLE",
                            "i-0cb2b964d3EXAMPLE"
                        ],
                        "Key": "InstanceIds"
                    }
                ],
                "WindowTargetId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }
        ]
    }

**Example 2: To list all targets for a maintenance window matching a specific owner information value**

The following ``describe-maintenance-window-targets`` example lists all of the targets for a maintenance window with a specific value. ::

    aws ssm describe-maintenance-window-targets \
        --window-id "mw-0ecb1226ddEXAMPLE" \
        --filters "Key=OwnerInformation,Values=CostCenter1"

Output::

    {
        "Targets": [
            {
                "WindowId": "mw-0ecb1226ddEXAMPLE",
                "WindowTargetId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "ResourceType": "INSTANCE",
                "Targets": [
                    {
                        "Key": "tag:Environment",
                        "Values": [
                            "Prod"
                        ]
                    }
                ],
                "OwnerInformation": "CostCenter1",
                "Name": "ProdTarget1"
            }
        ]
    }

For more information, see `View Information About Maintenance Windows (AWS CLI) <https://docs.aws.amazon.com/systems-manager/latest/userguide/maintenance-windows-cli-tutorials-describe.html>`__ in the *AWS Systems Manager User Guide*.
