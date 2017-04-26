**To get details of an association**

This example describes the association between an instance and a document.

Command::

  aws ssm describe-association --instance-id "i-0000293ffd8c57862" --name "AWS-UpdateSSMAgent"

Output::

  {
    "AssociationDescription": {
        "Status": {
            "Date": 1487876122.564,
            "Message": "Associated with AWS-UpdateSSMAgent",
            "Name": "Associated"
        },
        "Name": "AWS-UpdateSSMAgent",
        "InstanceId": "i-0000293ffd8c57862",
        "Overview": {
            "Status": "Pending",
            "DetailedStatus": "Associated",
            "AssociationStatusAggregatedCount": {
                "Pending": 1
            }
        },
        "AssociationId": "d8617c07-2079-4c18-9847-1655fc2698b0",
        "DocumentVersion": "$DEFAULT",
        "LastUpdateAssociationDate": 1487876122.564,
        "Date": 1487876122.564,
        "Targets": [
            {
                "Values": [
                    "i-0000293ffd8c57862"
                ],
                "Key": "InstanceIds"
            }
        ]
    }
  }
