**To describe the status of an instance's associations**

The following ``describe-instance-associations-status`` example shows details of the associations for an instance. ::

    aws ssm describe-instance-associations-status \
        --instance-id "i-1234567890abcdef0"

Output::

    {
        "InstanceAssociationStatusInfos": [
            {
                "AssociationId": "8dfe3659-4309-493a-8755-0123456789ab",
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
                "AssociationId": "5c5a31f6-6dae-46f9-944c-0123456789ab",
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
