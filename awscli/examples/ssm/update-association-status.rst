**To update the association status**

This example updates the association status of the association between an instance and a document.

Command::

  aws ssm update-association-status --name "AWS-UpdateSSMAgent" --instance-id "i-0000293ffd8c57862" --association-status "Date=1424421071.939,Name=Pending,Message=temp_status_change,AdditionalInfo=Additional-Config-Needed"

Output::

  {
    "AssociationDescription": {
        "Status": {
            "Date": 1424421071.0,
            "AdditionalInfo": "Additional-Config-Needed",
            "Message": "temp_status_change",
            "Name": "Pending"
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
