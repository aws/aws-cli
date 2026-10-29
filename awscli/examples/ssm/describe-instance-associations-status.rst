**To describe the status of an instance's associations**

The following ``describe-instance-associations-status`` example shows details of the associations for an instance. ::

    aws ssm describe-instance-associations-status \
        --instance-id "i-1234567890abcdef0"

Output::

    {
        "InstanceAssociationStatusInfos": [
            {
                "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Name": "AWS-GatherSoftwareInventory",
                "DocumentVersion": "1",
                "AssociationVersion": "1",
                "InstanceId": "i-1234567890abcdef0",
                "ExecutionDate": 1550501886.0,
                "Status": "Success",
                "ExecutionSummary": "1 out of 1 plugin processed, 1 success, 0 failed, 0 timedout, 0 skipped. ",
                "AssociationName": "Inventory-Association"
            },
            {
                "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Name": "AWS-UpdateSSMAgent",
                "DocumentVersion": "1",
                "AssociationVersion": "1",
                "InstanceId": "i-1234567890abcdef0",
                "ExecutionDate": 1550505828.548,
                "Status": "Success",
                "DetailedStatus": "Success",
                "AssociationName": "UpdateSSMAgent"
            }
        ]
    }

For more information, see `Working with associations in Systems Manager <https://docs.aws.amazon.com/systems-manager/latest/userguide/state-manager-associations.html>`__ in the *AWS Systems Manager User Guide*.
