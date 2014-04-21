**To create a VPC peering connection between your VPCs**

This example requests a peering connection between your VPCs vpc-1a2b3c4d and vpc-11122233.

Command::

  aws ec2 create-vpc-peering-connection --vpc-id vpc-1a2b3c4d --peer-vpc-id vpc-11122233

Output::

    {
        "VpcPeeringConnection": {
            "Status": {
                "Message": "Initiating Request to 444455556666",
                "Code": "initiating-request"
            },
            "Tags": [],
            "RequesterVpcInfo": {
                "OwnerId": "444455556666",
                "VpcId": "vpc-1a2b3c4d",
                "CidrBlock": "10.0.0.0/28"
            },
            "VpcPeeringConnectionId": "pcx-111aaa111",
            "ExpirationTime": "2014-04-02T16:13:36.000Z",
            "AccepterVpcInfo": {
                "OwnerId": "444455556666",
                "VpcId": "vpc-11122233"
            }
        }
    }

**To create a VPC peering connection with a VPC in another account**

This example requests a peering connection between your VPC (vpc-1a2b3c4d), and a VPC (vpc-123abc45) that belongs AWS account 123456789012.

Command::

  aws ec2 create-vpc-peering-connection --vpc-id vpc-1a2b3c4d --peer-vpc-id vpc-11122233 --peer-owner-id 123456789012

