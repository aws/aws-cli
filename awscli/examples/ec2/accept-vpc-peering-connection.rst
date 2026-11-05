**To accept a VPC peering connection**

The following ``accept-vpc-peering-connection`` example accepts the specified VPC peering connection request. ::

    aws ec2 accept-vpc-peering-connection \
        --vpc-peering-connection-id pcx-1a2b3c4d

Output::

    {
        "VpcPeeringConnection": {
            "Status": {
                "Message": "Provisioning",
                "Code": "provisioning"
            },
            "Tags": [],
            "AccepterVpcInfo": {
                "OwnerId": "123456789012",
                "VpcId": "vpc-44455566",
                "CidrBlock": "10.0.1.0/28"
            },
            "VpcPeeringConnectionId": "pcx-1a2b3c4d",
            "RequesterVpcInfo": {
                "OwnerId": "123456789012",
                "VpcId": "vpc-111abc45",
                "CidrBlock": "10.0.0.0/28"
            }
        }
    }

For more information, see `Accept or reject a VPC peering connection <https://docs.aws.amazon.com/vpc/latest/peering/accept-vpc-peering-connection.html>`__ in the *Amazon VPC Peering Guide*.
