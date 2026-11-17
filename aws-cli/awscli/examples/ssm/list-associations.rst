**Example 1: To list your associations for a specific instance**

The following ``list-associations`` example lists all associations with the AssociationName, UpdateSSMAgent. ::

    aws ssm list-associations \
        --association-filter-list "key=AssociationName,value=UpdateSSMAgent"

Output::

    {
        "Associations": [
            {
                "Name": "AWS-UpdateSSMAgent",
                "InstanceId": "i-1234567890abcdef0",
                "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "AssociationVersion": "1",
                "Targets": [
                    {
                        "Key": "InstanceIds",
                        "Values": [
                            "i-016648b75dd622dab"
                        ]
                    }
                ],
                "Overview": {
                    "Status": "Pending",
                    "DetailedStatus": "Associated",
                    "AssociationStatusAggregatedCount": {
                        "Pending": 1
                    }
                },
                "ScheduleExpression": "cron(0 00 12 ? * SUN *)",
                "AssociationName": "UpdateSSMAgent"
            }
        ]
    }

For more information, see `Working with associations in Systems Manager <https://docs.aws.amazon.com/systems-manager/latest/userguide/state-manager-associations.html>`__ in the *Systems Manager User Guide*.

**Example 2: To list your associations for a specific document**

The following ``list-associations`` example lists all associations for the specified document. ::

    aws ssm list-associations \
        --association-filter-list "key=Name,value=AWS-UpdateSSMAgent"

Output::

    {
        "Associations": [
            {
                "Name": "AWS-UpdateSSMAgent",
                "InstanceId": "i-1234567890abcdef0",
                "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "AssociationVersion": "1",
                "Targets": [
                    {
                        "Key": "InstanceIds",
                        "Values": [
                            "i-1234567890abcdef0"
                        ]
                    }
                ],
                "LastExecutionDate": 1550505828.548,
                "Overview": {
                    "Status": "Success",
                    "DetailedStatus": "Success",
                    "AssociationStatusAggregatedCount": {
                        "Success": 1
                    }
                },
                "ScheduleExpression": "cron(0 00 12 ? * SUN *)",
                "AssociationName": "UpdateSSMAgent"
            },
        {
                "Name": "AWS-UpdateSSMAgent",
                "InstanceId": "i-9876543210abcdef0",
                "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "AssociationVersion": "1",
                "Targets": [
                    {
                        "Key": "InstanceIds",
                        "Values": [
                            "i-9876543210abcdef0"
                        ]
                    }
                ],
                "LastExecutionDate": 1550507531.0,
                "Overview": {
                    "Status": "Success",
                    "AssociationStatusAggregatedCount": {
                        "Success": 1
                    }
                }
            }
        ]
    }

For more information, see `Working with associations in Systems Manager <https://docs.aws.amazon.com/systems-manager/latest/userguide/state-manager-associations.html>`__ in the *Systems Manager User Guide*.