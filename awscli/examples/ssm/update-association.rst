**To update a document association**

This example updates an association with a new document version.

Command::

  aws ssm update-association --association-id "8dfe3659-4309-493a-8755-0123456789ab" --document-version "\$LATEST"

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
        "AssociationId": "8dfe3659-4309-493a-8755-0123456789ab",
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

**To update the schedule expression of an association**

This example updates the schedule expression for the specified association.

Command::

  aws ssm update-association --association-id "8dfe3659-4309-493a-8755-0123456789ab" --schedule-expression "cron(0 0 0/4 1/1 * ? *)"

