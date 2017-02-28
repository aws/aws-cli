**To describe instance information**

This example shows details of each of your instances.

Command::

  aws ssm describe-instance-information

Output::

  {
    "InstanceInformationList": [
        {
            "IsLatestVersion": true,
            "LastSuccessfulAssociationExecutionDate": 1487876123.0,
            "ComputerName": "ip-172-31-44-222.us-west-2.compute.internal",
            "PingStatus": "Online",
            "InstanceId": "i-0cb2b964d3e14fd9f",
            "IPAddress": "172.31.44.222",
            "AssociationStatus": "Success",
            "LastAssociationExecutionDate": 1487876123.0,
            "ResourceType": "EC2Instance",
            "AgentVersion": "2.0.672.0",
            "PlatformVersion": "2016.09",
            "AssociationOverview": {
                "InstanceAssociationStatusAggregatedCount": {
                    "Success": 1
                }
            },
            "PlatformName": "Amazon Linux AMI",
            "PlatformType": "Linux",
            "LastPingDateTime": 1487898903.758
        }
    ]
  }

**To describe information about a specific instance**

This example shows details of instance ``i-0cb2b964d3e14fd9f``.

Command::

  aws ssm describe-instance-information --instance-information-filter-list "key=InstanceIds,valueSet=i-0cb2b964d3e14fd9f"
