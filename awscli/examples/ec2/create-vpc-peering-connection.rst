**Example 1: To create a VPC peering connection between your VPCs**

The following ``create-vpc-peering-connection`` example requests a peering connection between your VPCs vpc-1a2b3c4d and vpc-11122233. ::

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

**Example 2: To create a VPC peering connection with a VPC in another account**

The following ``create-vpc-peering-connection`` example requests a peering connection between your VPC (vpc-1a2b3c4d), and a VPC (vpc-11122233) that belongs to AWS account 123456789012. ::

    aws ec2 create-vpc-peering-connection --vpc-id vpc-1a2b3c4d --peer-vpc-id vpc-11122233 --peer-owner-id 123456789012

**Example 3: To create a VPC peering connection with a VPC in a different region**

The following ``create-vpc-peering-connection`` example requests a peering connection between your VPC in the current region (vpc-1a2b3c4d), and a VPC (vpc-11122233) in your account in the ``us-west-2`` region. ::

    aws ec2 create-vpc-peering-connection --vpc-id vpc-1a2b3c4d --peer-vpc-id vpc-11122233 --peer-region us-west-2

The following ``create-vpc-peering-connection`` example requests a peering connection between your VPC in the current region (vpc-1a2b3c4d), and a VPC (vpc-11122233) that belongs to AWS account 123456789012 that's in the ``us-west-2`` region. ::

    aws ec2 create-vpc-peering-connection --vpc-id vpc-1a2b3c4d --peer-vpc-id vpc-11122233 --peer-owner-id 123456789012 --peer-region us-west-2