**To associate a document using instance IDs**

This example associates a configuration document with an instance, using instance IDs.

Command::

  aws ssm create-association --instance-id "i-0cb2b964d3e14fd9f" --name "AWS-UpdateSSMAgent"

Output::

  {
    "AssociationDescription": {
        "Status": {
            "Date": 1487875500.33,
            "Message": "Associated with AWS-UpdateSSMAgent",
            "Name": "Associated"
        },
        "Name": "AWS-UpdateSSMAgent",
        "InstanceId": "i-0cb2b964d3e14fd9f",
        "Overview": {
            "Status": "Pending",
            "DetailedStatus": "Creating"
        },
        "AssociationId": "b7c3266e-a544-44db-877e-b20d3a108189",
        "DocumentVersion": "$DEFAULT",
        "LastUpdateAssociationDate": 1487875500.33,
        "Date": 1487875500.33,
        "Targets": [
            {
                "Values": [
                    "i-0cb2b964d3e14fd9f"
                ],
                "Key": "InstanceIds"
            }
        ]
    }
  }

**To associate a document using targets**

This example associates a configuration document with an instance, using targets.

Command::

  aws ssm create-association --name "AWS-UpdateSSMAgent" --targets "Key=instanceids,Values=i-0cb2b964d3e14fd9f"
  