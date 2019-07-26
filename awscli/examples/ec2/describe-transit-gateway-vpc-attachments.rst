**To describe your transit gateway VPC attachments**

The following ``describe-transit-gateway-vpc-attachments`` example describes your transit gateway VPC attachments. ::

    aws ec2 describe-transit-gateway-vpc-attachments

Output::

    {
        "TransitGatewayVpcAttachments": [
            {
                "TransitGatewayAttachmentId": "tgw-attach-071e4b4c00EXAMPLE",
                "TransitGatewayId": "tgw-02f776b1a7EXAMPLE",
                "VpcId": "vpc-0065acced4EXAMPLE",
                "VpcOwnerId": "111122223333",
                "State": "available",
                "SubnetIds": [
                    "subnet-0187aff814EXAMPLE"
                ],
                "CreationTime": "2019-07-17T15:19:21.000Z",
                "Options": {
                    "DnsSupport": "enable",
                    "Ipv6Support": "disable"
                },
                "Tags": []
            }
        ]
    }

For more information, see `View Your VPC Attachments <https://docs.aws.amazon.com/vpc/latest/tgw/tgw-vpc-attachments.html#view-vpc-attachment>`__ in the *Amazon VPC Transit Gateways Guide*.
