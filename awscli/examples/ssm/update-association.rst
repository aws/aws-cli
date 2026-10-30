**Example 1: To update a document association**

The following ``update-association`` example updates an association with a new document version. ::

    aws ssm update-association \
        --association-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --document-version "\$LATEST"

Output::

    {
        "AssociationDescription": {
            "Name": "AWS-UpdateSSMAgent",
            "AssociationVersion": "2",
            "Date": 1550508093.293,
            "LastUpdateAssociationDate": 1550508106.596,
            "Overview": {
                "Status": "Pending",
                "DetailedStatus": "Creating"
            },
            "DocumentVersion": "$LATEST",
            "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "Targets": [
                {
                    "Key": "tag:Name",
                    "Values": [
                        "Linux"
                    ]
                }
            ],
            "LastExecutionDate": 1550508094.879,
            "LastSuccessfulExecutionDate": 1550508094.879
        }
    }

For more information, see `Editing and creating a new version of an association <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-state-assoc-edit.html>`__ in the *AWS Systems Manager User Guide*.

**Example 2: To update the schedule expression of an association**

The following ``update-association`` example updates the schedule expression for the specified association. ::

    aws ssm update-association \
        --association-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --schedule-expression "cron(0 0 0/4 1/1 * ? *)"

Output::

    {
        "AssociationDescription": {
            "Name": "AWS-HelloWorld",
            "AssociationVersion": "2",
            "Date": "2021-02-08T13:54:19.203000-08:00",
            "LastUpdateAssociationDate": "2021-06-29T11:51:07.933000-07:00",
            "Overview": {
                "Status": "Pending",
                "DetailedStatus": "Creating"
            },
            "DocumentVersion": "$DEFAULT",
            "AssociationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "Targets": [
                {
                    "Key": "aws:NoOpAutomationTag",
                    "Values": [
                        "AWS-NoOpAutomationTarget-Value"
                    ]
                }
            ],
            "ScheduleExpression": "cron(0 0 0/4 1/1 * ? *)",
            "LastExecutionDate": "2021-06-26T19:00:48.110000-07:00",
            "ApplyOnlyAtCronInterval": false
        }
    }

For more information, see `Editing and creating a new version of an association <https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-state-assoc-edit.html>`__ in the *AWS Systems Manager User Guide*.