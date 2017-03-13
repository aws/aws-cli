**To update a document association**

This example updates an association with a new document version.

Command::

  aws ssm update-association --association-id "4cc73e42-d5ae-4879-84f8-57e09c0efcd0" --document-version "\$LATEST"

Output::

  {
    "AssociationDescription": {
        "LastSuccessfulExecutionDate": 1487906247.0,
        "Name": "AWS-UpdateSSMAgent",
        "LastExecutionDate": 1487906247.0,
        "Overview": {
            "Status": "Success",
            "AssociationStatusAggregatedCount": {
                "Success": 1
            }
        },
        "AssociationId": "4cc73e42-d5ae-4879-84f8-57e09c0efcd0",
        "DocumentVersion": "$LATEST",
        "LastUpdateAssociationDate": 1487906288.447,
        "Date": 1487906246.999,
        "Targets": [
            {
                "Values": [
                    "i-0cb2b964d3e14fd9f"
                ],
                "Key": "instanceids"
            }
        ]
    }
  }
