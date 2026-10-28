**Example 1: To describe your VPC peering connections**

The following ``describe-vpc-peering-connections`` example describes all of your VPC peering connections. ::

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
                    "PeeringOptions": {
                        "AllowEgressFromLocalVpcToRemoteClassicLink": false,
                        "AllowEgressFromLocalClassicLinkToRemoteVpc": false
                    },
                    "OwnerId": "444455556666",
                    "VpcId": "vpc-123abc45",
                    "CidrBlock": "192.168.0.0/16"
                }
            },
            {
                "Status": {
                    "Message": "Pending Acceptance by 444455556666",
                    "Code": "pending-acceptance"
                },
                "Tags": [],
                "RequesterVpcInfo": {
                    "PeeringOptions": {
                        "AllowEgressFromLocalVpcToRemoteClassicLink": false,
                        "AllowEgressFromLocalClassicLinkToRemoteVpc": false
                    },
                    "OwnerId": "444455556666",
                    "VpcId": "vpc-11aa22bb",
                    "CidrBlock": "10.0.0.0/28"
                },
                "VpcPeeringConnectionId": "pcx-abababab",
                "ExpirationTime": "2014-04-03T09:12:43.000Z",
                "AccepterVpcInfo": {
                    "OwnerId": "444455556666",
                    "VpcId": "vpc-33cc44dd"
                }
            }
        ]
    }


**Example 2: To describe specific VPC peering connections**

The following ``describe-vpc-peering-connections`` example describes all of your VPC peering connections that are in the pending-acceptance state. ::

    aws ec2 describe-vpc-peering-connections \
        --filters Name=status-code,Values=pending-acceptance


The following ``describe-vpc-peering-connections`` example describes all of your VPC peering connections that have the tag Owner=Finance. ::

    aws ec2 describe-vpc-peering-connections \
        --filters Name=tag:Owner,Values=Finance


The following ``describe-vpc-peering-connections`` example describes all of the VPC peering connections you requested for the specified VPC, vpc-1a2b3c4d. ::

    aws ec2 describe-vpc-peering-connections \
        --filters Name=requester-vpc-info.vpc-id,Values=vpc-1a2b3c4d

