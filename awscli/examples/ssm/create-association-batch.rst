**To create multiple associations**

This example associates a configuration document with multiple instances. The output returns a list of successful and failed operations, if applicable.

Command::

  aws ssm create-association-batch --entries "Name=AWS-UpdateSSMAgent,InstanceId=i-0cb2b964d3e14fd9f" "Name=AWS-UpdateSSMAgent,InstanceId=i-0000293ffd8c57862"

Output::

  {
    "Successful": [
        {
            "Status": {
                "Date": 1487876122.564,
                "Message": "Associated with AWS-UpdateSSMAgent",
                "Name": "Associated"
            },
            "Name": "AWS-UpdateSSMAgent",
            "InstanceId": "i-0000293ffd8c57862",
            "Overview": {
                "Status": "Pending",
                "DetailedStatus": "Creating"
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
        },
        {
            "Status": {
                "Date": 1487876122.595,
                "Message": "Associated with AWS-UpdateSSMAgent",
                "Name": "Associated"
            },
            "Name": "AWS-UpdateSSMAgent",
            "InstanceId": "i-0cb2b964d3e14fd9f",
            "Overview": {
                "Status": "Pending",
                "DetailedStatus": "Creating"
            },
            "AssociationId": "2ccfbc46-5fe4-4e5c-ba46-70b56cc93f53",
            "DocumentVersion": "$DEFAULT",
            "LastUpdateAssociationDate": 1487876122.595,
            "Date": 1487876122.595,
            "Targets": [
                {
                    "Values": [
                        "i-0cb2b964d3e14fd9f"
                    ],
                    "Key": "InstanceIds"
                }
            ]
        }
    ],
    "Failed": []
  }
