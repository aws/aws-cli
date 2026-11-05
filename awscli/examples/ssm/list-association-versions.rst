**To list all versions of an association for a specific association ID**

The following ``list-association-versions`` example lists all versions of the specified associations. ::

    aws ssm list-association-versions \
        --association-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
    "AssociationVersions": [
            {
                "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "AssociationVersion": "1",
                "CreatedDate": 1550505536.726,
                "Name": "AWS-UpdateSSMAgent",
                "Parameters": {
                    "allowDowngrade": [
                        "false"
                    ],
                    "version": [
                        ""
                    ]
                },
                "Targets": [
                    {
                        "Key": "InstanceIds",
                        "Values": [
                            "i-1234567890abcdef0"
                        ]
                    }
                ],
                "ScheduleExpression": "cron(0 00 12 ? * SUN *)",
                "AssociationName": "UpdateSSMAgent"
            }
        ]
    }

For more information, see `Working with associations in Systems Manager  <https://docs.aws.amazon.com/systems-manager/latest/userguide/state-manager-associations.html>`__ in the *AWS Systems Manager User Guide*.