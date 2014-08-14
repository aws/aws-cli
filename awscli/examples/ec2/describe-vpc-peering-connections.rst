**To describe your VPC peering connections**

This example describes all of your VPC peering connections.

Command::

  aws ec2 describe-vpc-peering-connections

Output::

    {
        "VpcPeeringConnections": [
            {
                "Status": {
                    "Message": "Active",
                    "Code": "active"
                },
                "Tags": [
                    {
                        "Value": "Peering-1",
                        "Key": "Name"
                    }
                ],
                "AccepterVpcInfo": {
                    "OwnerId": "111122223333",
                    "VpcId": "vpc-1a2b3c4d",
                    "CidrBlock": "10.0.1.0/28"
                },
                "VpcPeeringConnectionId": "pcx-11122233",
                "RequesterVpcInfo": {
                    "OwnerId": "444455556666",
                    "VpcId": "vpc-123abc45",
                    "CidrBlock": "10.0.0.0/28"
                }
            },
            {
                "Status": {
                    "Message": "Pending Acceptance by 123456789123",
                    "Code": "pending-acceptance"
                },
                "Tags": [
                    {
                        "Value": null,
                        "Key": "Name"
                    }
                ],
                "RequesterVpcInfo": {
                    "OwnerId": "123456789123",
                    "VpcId": "vpc-11aa22bb",
                    "CidrBlock": "10.0.0.0/28"
                },
                "VpcPeeringConnectionId": "pcx-abababab",
                "ExpirationTime": "2014-04-03T09:12:43.000Z",
                "AccepterVpcInfo": {
                    "OwnerId": "123456789123",
                    "VpcId": "vpc-33cc44dd"
                }
            }
        ]
    }


**To describe specific VPC peering connections**

This example describes all of your VPC peering connections that are in the pending-acceptance state.

Command::

  aws ec2 describe-vpc-peering-connections --filters Name=status-code,Values=pending-acceptance


This example describes all of your VPC peering connections that have the tag Name=Finance or Name=Accounts.

Command::

  aws ec2 describe-vpc-peering-connections --filters Name=tag-key,Values=Name Name=tag-value,Values=Finance,Accounts


This example describes all of the VPC peering connections you requested for the specified VPC, vpc-1a2b3c4d.

Command::

  aws ec2 describe-vpc-peering-connections --filters Name=requester-vpc-info.vpc-id,Values=vpc-1a2b3c4d

