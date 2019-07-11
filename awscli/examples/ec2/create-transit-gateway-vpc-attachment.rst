**To associate a Transit Gateway with a VPC**

The following ``create-transit-gateway-vpc-attachment`` example creates a transit gateway attachment to the specified VPC. ::

    aws ec2 create-transit-gateway-vpc-attachment \
        --transit-gateway-id tgw-0262a0e521EXAMPLE \
        --vpc-id vpc-07e8ffd50f49335df \
        --subnet-id subnet-0752213d59efde95a

Output::

    {
        "TransitGatewayVpcAttachment": {
            "TransitGatewayAttachmentId": "tgw-attach-0a34fe6b4fea0ff4a",
            "TransitGatewayId": "tgw-0262a0e521EXAMPLE",
            "VpcId": "vpc-07e8ffd50fEXAMPLE",
            "VpcOwnerId": "111122223333",
            "State": "pending",
            "SubnetIds": [
                "subnet-0752213d59efde95a"
            ],
            "CreationTime": "2019-07-10T17:33:46.000Z",
            "Options": {
                "DnsSupport": "enable",
                "Ipv6Support": "disable"
            }
        }
    }

For more information, see `Create a Transit Gateway Attachment to a VPC <https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpc-attachments.html#create-vpc-attachment>`__ in the *AWS Transit Gateways Guide*.
