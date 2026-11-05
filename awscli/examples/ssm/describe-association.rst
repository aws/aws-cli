**Example 1: To get details of an association**

The following ``describe-association`` example describes the association for the specified association ID. ::

    aws ssm describe-association \
        --association-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "AssociationDescription": {
            "Name": "AWS-GatherSoftwareInventory",
            "AssociationVersion": "1",
            "Date": 1534864780.995,
            "LastUpdateAssociationDate": 1543235759.81,
            "Overview": {
                "Status": "Success",
                "AssociationStatusAggregatedCount": {
                    "Success": 2
                }
            },
            "DocumentVersion": "$DEFAULT",
            "Parameters": {
                "applications": [
                    "Enabled"
                ],
                "awsComponents": [
                    "Enabled"
                ],
                "customInventory": [
                    "Enabled"
                ],
                "files": [
                    ""
                ],
                "instanceDetailedInformation": [
                    "Enabled"
                ],
                "networkConfig": [
                    "Enabled"
                ],
                "services": [
                    "Enabled"
                ],
                "windowsRegistry": [
                    ""
                ],
                "windowsRoles": [
                    "Enabled"
                ],
                "windowsUpdates": [
                    "Enabled"
                ]
            },
            "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "Targets": [
                {
                    "Key": "InstanceIds",
                    "Values": [
                        "*"
                    ]
                }
            ],
            "ScheduleExpression": "rate(24 hours)",
            "LastExecutionDate": 1550501886.0,
            "LastSuccessfulExecutionDate": 1550501886.0,
            "AssociationName": "Inventory-Association"
        }
    }

For more information, see `Editing and creating a new version of an association <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-state-assoc-edit.html>`__ in the *AWS Systems Manager User Guide*.

**Example 2: To get details of an association for a specific instance and document**

The following ``describe-association`` example describes the association between an instance and a document. ::

    aws ssm describe-association \
        --instance-id "i-1234567890abcdef0" \
        --name "AWS-UpdateSSMAgent"

Output::

    {
        "AssociationDescription": {
            "Status": {
                "Date": 1487876122.564,
                "Message": "Associated with AWS-UpdateSSMAgent",
                "Name": "Associated"
            },
            "Name": "AWS-UpdateSSMAgent",
            "InstanceId": "i-1234567890abcdef0",
            "Overview": {
                "Status": "Pending",
                "DetailedStatus": "Associated",
                "AssociationStatusAggregatedCount": {
                    "Pending": 1
                }
            },
            "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "DocumentVersion": "$DEFAULT",
            "LastUpdateAssociationDate": 1487876122.564,
            "Date": 1487876122.564,
            "Targets": [
                {
                    "Values": [
                        "i-1234567890abcdef0"
                    ],
                    "Key": "InstanceIds"
                }
            ]
        }
    }

For more information, see `Editing and creating a new version of an association <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-state-assoc-edit.html>`__ in the *AWS Systems Manager User Guide*.