**Example 1: To create a VPC peering connection between your VPCs**

The following ``create-vpc-peering-connection`` example requests a peering connection between your VPCs vpc-1a2b3c4d and vpc-11122233. ::

    aws ec2 create-vpc-peering-connection \
        --vpc-id vpc-1a2b3c4d \
        --peer-vpc-id vpc-11122233

Output::

    {
        "VpcPeeringConnection": {
            "Status": {
                "Message": "Initiating Request to 123456789012",
                "Code": "initiating-request"
            },
            "Tags": [],
            "RequesterVpcInfo": {
                "OwnerId": "123456789012",
                "VpcId": "vpc-1a2b3c4d",
                "CidrBlock": "10.0.0.0/28"
            },
            "VpcPeeringConnectionId": "pcx-111aaa111",
            "ExpirationTime": "2014-04-02T16:13:36.000Z",
            "AccepterVpcInfo": {
                "OwnerId": "123456789012",
                "VpcId": "vpc-11122233"
            }
        }
    }

For more information, see `Create a VPC peering connection <https://docs.aws.amazon.com/vpc/latest/peering/create-vpc-peering-connection.html>`__ in the *Amazon VPC Peering Guide*.

**Example 2: To create a VPC peering connection with a VPC in another account**

The following ``create-vpc-peering-connection`` example requests a peering connection between your VPC (vpc-1a2b3c4d), and a VPC (vpc-11122233) that belongs to AWS account 123456789111. ::

    aws ec2 create-vpc-peering-connection \
        --vpc-id vpc-1a2b3c4d \
        --peer-vpc-id vpc-11122233 \
        --peer-owner-id 123456789111

Output::

    {
        "VpcPeeringConnection": {
            "Status": {
                "Message": "Initiating Request to 123456789111",
                "Code": "initiating-request"
            },
            "Tags": [],
            "RequesterVpcInfo": {
                "OwnerId": "123456789012",
                "VpcId": "vpc-1a2b3c4d",
                "CidrBlock": "10.0.0.0/28"
            },
            "VpcPeeringConnectionId": "pcx-222bbb222",
            "ExpirationTime": "2014-04-02T16:13:36.000Z",
            "AccepterVpcInfo": {
                "OwnerId": "123456789111",
                "VpcId": "vpc-11122233"
            }
        }
    }

For more information, see `Create a VPC peering connection <https://docs.aws.amazon.com/vpc/latest/peering/create-vpc-peering-connection.html>`__ in the *Amazon VPC Peering Guide*.

**Example 3: To create a VPC peering connection with a VPC in a different region**

The following ``create-vpc-peering-connection`` example requests a peering connection between your VPC in the current region (vpc-1a2b3c4d), and a VPC (vpc-11122233) in your account in the ``us-west-2`` region. ::

    aws ec2 create-vpc-peering-connection \
        --vpc-id vpc-1a2b3c4d \
        --peer-vpc-id vpc-11122233 \
        --peer-region us-west-2

Output::

    {
        "VpcPeeringConnection": {
            "Status": {
                "Message": "Initiating Request to 123456789012",
                "Code": "initiating-request"
            },
            "Tags": [],
            "RequesterVpcInfo": {
                "OwnerId": "123456789012",
                "VpcId": "vpc-1a2b3c4d",
                "CidrBlock": "10.0.0.0/28"
            },
            "VpcPeeringConnectionId": "pcx-333ccc333",
            "ExpirationTime": "2014-04-02T16:13:36.000Z",
            "AccepterVpcInfo": {
                "OwnerId": "123456789012",
                "VpcId": "vpc-11122233",
                "Region": "us-west-2"
            }
        }
    }

The following ``create-vpc-peering-connection`` example requests a peering connection between your VPC in the current region (vpc-1a2b3c4d), and a VPC (vpc-11122233) that belongs to AWS account 123456789111 that's in the ``us-west-2`` region. ::

    aws ec2 create-vpc-peering-connection \
        --vpc-id vpc-1a2b3c4d \
        --peer-vpc-id vpc-11122233 \
        --peer-owner-id 123456789111 \
        --peer-region us-west-2

Output::

    {
        "VpcPeeringConnection": {
            "Status": {
                "Message": "Initiating Request to 123456789111",
                "Code": "initiating-request"
            },
            "Tags": [],
            "RequesterVpcInfo": {
                "OwnerId": "123456789012",
                "VpcId": "vpc-1a2b3c4d",
                "CidrBlock": "10.0.0.0/28"
            },
            "VpcPeeringConnectionId": "pcx-444ddd444",
            "ExpirationTime": "2014-04-02T16:13:36.000Z",
            "AccepterVpcInfo": {
                "OwnerId": "123456789111",
                "VpcId": "vpc-11122233",
                "Region": "us-west-2"
            }
        }
    }

For more information, see `Create a VPC peering connection <https://docs.aws.amazon.com/vpc/latest/peering/create-vpc-peering-connection.html>`__ in the *Amazon VPC Peering Guide*.
