**To get details of an association execution**

This example describes the specified association execution.

Command::

  aws ssm describe-association-execution-targets --association-id "8dfe3659-4309-493a-8755-0123456789ab" --execution-id "7abb6378-a4a5-4f10-8312-0123456789ab"

Output::

  {
    "AssociationExecutionTargets": [
        {
            "AssociationId": "8dfe3659-4309-493a-8755-0123456789ab",
            "AssociationVersion": "1",
            "ExecutionId": "7abb6378-a4a5-4f10-8312-0123456789ab",
            "ResourceId": "i-1234567890abcdef0",
            "ResourceType": "ManagedInstance",
            "Status": "Success",
            "DetailedStatus": "Success",
            "LastExecutionDate": 1550505538.497,
            "OutputSource": {
                "OutputSourceId": "97fff367-fc5a-4299-aed8-0123456789ab",
                "OutputSourceType": "RunCommand"
            }
        }
    ]
  }
