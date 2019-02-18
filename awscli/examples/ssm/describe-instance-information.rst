**To describe managed instance information**

This example shows details of each of your managed instances.

Command::

  aws ssm describe-instance-information

Output::

  {
    "InstanceInformationList": [
        {
            "InstanceId": "i-1234567890abcdef0",
            "PingStatus": "Online",
            "LastPingDateTime": 1550501835.178,
            "AgentVersion": "2.3.415.0",
            "IsLatestVersion": false,
            "PlatformType": "Linux",
            "PlatformName": "Amazon Linux AMI",
            "PlatformVersion": "2018.03",
            "ResourceType": "EC2Instance",
            "IPAddress": "172.16.0.154",
            "ComputerName": "ip-172-16-0-154.ec2.internal",
            "AssociationStatus": "Success",
            "LastAssociationExecutionDate": 1550501837.0,
            "LastSuccessfulAssociationExecutionDate": 1550501837.0,
            "AssociationOverview": {
                "InstanceAssociationStatusAggregatedCount": {
                    "Success": 1
                }
            }
        },
        ...
    ]
  }

**To describe information about a specific managed instance**

This example shows details of the managed instance ``i-1234567890abcdef0``.

Command::

  aws ssm describe-instance-information --filters "Key=InstanceIds,Values=i-1234567890abcdef0"

**To describe information about managed instances with a specific tag key**

This example shows details for managed instances that have the tag key ``DEV``.

Command::

  aws ssm describe-instance-information --filters "Key=tag-key,Values=DEV"
