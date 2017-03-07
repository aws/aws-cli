**To list your associations for a specific instance**

This example lists all the associations for an instance.

Command::

  aws ssm list-associations --association-filter-list "key=InstanceId,value=i-0000293ffd8c57862"

Output::

  {
    "Associations": [
        {
            "InstanceId": "i-0000293ffd8c57862",
            "Overview": {
                "Status": "Pending",
                "DetailedStatus": "Associated",
                "AssociationStatusAggregatedCount": {
                    "Pending": 1
                }
            },
            "AssociationId": "d8617c07-2079-4c18-9847-1655fc2698b0",
            "Name": "AWS-UpdateSSMAgent",
            "Targets": [
                {
                    "Values": [
                        "i-0000293ffd8c57862"
                    ],
                    "Key": "InstanceIds"
                }
            ]
        }
    ]
  }

**To list your associations for a specific document**

This example lists all associations for the a document.

Command::

  aws ssm list-associations --association-filter-list "key=Name,value=AWS-UpdateSSMAgent"

Output::

  {
    "Associations": [
        {
            "InstanceId": "i-0000293ffd8c57862",
            "Overview": {
                "Status": "Pending",
                "DetailedStatus": "Associated",
                "AssociationStatusAggregatedCount": {
                    "Pending": 1
                }
            },
            "AssociationId": "d8617c07-2079-4c18-9847-1655fc2698b0",
            "Name": "AWS-UpdateSSMAgent",
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
            "Name": "AWS-UpdateSSMAgent",
            "LastExecutionDate": 1487876123.0,
            "InstanceId": "i-0cb2b964d3e14fd9f",
            "Overview": {
                "Status": "Success",
                "AssociationStatusAggregatedCount": {
                    "Success": 1
                }
            },
            "AssociationId": "2ccfbc46-5fe4-4e5c-ba46-70b56cc93f53",
            "Targets": [
                {
                    "Values": [
                        "i-0cb2b964d3e14fd9f"
                    ],
                    "Key": "InstanceIds"
                }
            ]
        }
    ]
  }
