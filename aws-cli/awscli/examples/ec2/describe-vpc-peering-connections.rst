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
                    "OwnerId": "123456789111",
                    "VpcId": "vpc-1a2b3c4d",
                    "CidrBlock": "10.0.1.0/28"
                },
                "VpcPeeringConnectionId": "pcx-11122233",
                "RequesterVpcInfo": {
                    "PeeringOptions": {
                        "AllowEgressFromLocalVpcToRemoteClassicLink": false,
                        "AllowEgressFromLocalClassicLinkToRemoteVpc": false
                    },
                    "OwnerId": "123456789222",
                    "VpcId": "vpc-123abc45",
                    "CidrBlock": "192.168.0.0/16"
                }
            },
            {
                "Status": {
                    "Message": "Pending Acceptance by 123456789222",
                    "Code": "pending-acceptance"
                },
                "Tags": [],
                "RequesterVpcInfo": {
                    "PeeringOptions": {
                        "AllowEgressFromLocalVpcToRemoteClassicLink": false,
                        "AllowEgressFromLocalClassicLinkToRemoteVpc": false
                    },
                    "OwnerId": "123456789222",
                    "VpcId": "vpc-11aa22bb",
                    "CidrBlock": "10.0.0.0/28"
                },
                "VpcPeeringConnectionId": "pcx-abababab",
                "ExpirationTime": "2014-04-03T09:12:43.000Z",
                "AccepterVpcInfo": {
                    "OwnerId": "123456789222",
                    "VpcId": "vpc-33cc44dd"
                }
            }
        ]
    }

For more information, see `VPC peering connections <https://docs.aws.amazon.com/vpc/latest/peering/working-with-vpc-peering.html>`__ in the *Amazon VPC Peering Guide*.

**Example 2: To describe specific VPC peering connections**

The following ``describe-vpc-peering-connections`` example describes all of your VPC peering connections that are in the pending-acceptance state. ::

    aws ec2 describe-vpc-peering-connections \
        --filters Name=status-code,Values=pending-acceptance

Output::

    {
        "VpcPeeringConnections": [
            {
                "Status": {
                    "Message": "Pending Acceptance by 123456789222",
                    "Code": "pending-acceptance"
                },
                "Tags": [],
                "RequesterVpcInfo": {
                    "PeeringOptions": {
                        "AllowEgressFromLocalVpcToRemoteClassicLink": false,
                        "AllowEgressFromLocalClassicLinkToRemoteVpc": false
                    },
                    "OwnerId": "123456789222",
                    "VpcId": "vpc-11aa22bb",
                    "CidrBlock": "10.0.0.0/28"
                },
                "VpcPeeringConnectionId": "pcx-abababab",
                "ExpirationTime": "2014-04-03T09:12:43.000Z",
                "AccepterVpcInfo": {
                    "OwnerId": "123456789222",
                    "VpcId": "vpc-33cc44dd"
                }
            }
        ]
    }


The following ``describe-vpc-peering-connections`` example describes all of your VPC peering connections that have the tag Owner=Finance. ::

    aws ec2 describe-vpc-peering-connections \
        --filters Name=tag:Owner,Values=Finance

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
                        "Value": "Finance",
                        "Key": "Owner"
                    }
                ],
                "AccepterVpcInfo": {
                    "OwnerId": "123456789222",
                    "VpcId": "vpc-44dd55ee",
                    "CidrBlock": "10.1.0.0/16"
                },
                "VpcPeeringConnectionId": "pcx-cdcdcdcd",
                "RequesterVpcInfo": {
                    "PeeringOptions": {
                        "AllowEgressFromLocalVpcToRemoteClassicLink": false,
                        "AllowEgressFromLocalClassicLinkToRemoteVpc": false
                    },
                    "OwnerId": "123456789222",
                    "VpcId": "vpc-123abc45",
                    "CidrBlock": "192.168.0.0/16"
                }
            }
        ]
    }


The following ``describe-vpc-peering-connections`` example describes all of the VPC peering connections you requested for the specified VPC, vpc-1a2b3c4d. ::

    aws ec2 describe-vpc-peering-connections \
        --filters Name=requester-vpc-info.vpc-id,Values=vpc-1a2b3c4d

Output::

    {
        "VpcPeeringConnections": [
            {
                "Status": {
                    "Message": "Active",
                    "Code": "active"
                },
                "Tags": [],
                "AccepterVpcInfo": {
                    "OwnerId": "123456789222",
                    "VpcId": "vpc-55ee66ff",
                    "CidrBlock": "172.31.0.0/16"
                },
                "VpcPeeringConnectionId": "pcx-efefefef",
                "RequesterVpcInfo": {
                    "PeeringOptions": {
                        "AllowEgressFromLocalVpcToRemoteClassicLink": false,
                        "AllowEgressFromLocalClassicLinkToRemoteVpc": false
                    },
                    "OwnerId": "123456789111",
                    "VpcId": "vpc-1a2b3c4d",
                    "CidrBlock": "10.0.1.0/28"
                }
            }
        ]
    }

For more information, see `VPC peering connections <https://docs.aws.amazon.com/vpc/latest/peering/working-with-vpc-peering.html>`__ in the *Amazon VPC Peering Guide*.
