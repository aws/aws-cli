**To describe the status of an instance's associations**

This example shows details of the associations for an instance.

Command::

  aws ssm describe-instance-associations-status --instance-id "i-0000293ffd8c57862"

Output::

  {
    "InstanceAssociationStatusInfos": [
        {
            "Status": "Pending",
            "DetailedStatus": "Associated",
            "Name": "AWS-UpdateSSMAgent",
            "InstanceId": "i-0000293ffd8c57862",
            "AssociationId": "d8617c07-2079-4c18-9847-1655fc2698b0",
            "DocumentVersion": "1"
        }
    ]
  }
