**To describe your transit gateways**

The following ``describe-transit-gateways`` example retrieves details about your transit gateways. ::

    aws ec2 describe-transit-gateways
    
Output::

    {
        "TransitGateways": [
            {
                "TransitGatewayId": "tgw-0262a0e521EXAMPLE",
                "TransitGatewayArn": "arn:aws:ec2:us-west-2:123456789012:transit-gateway/tgw-0262a0e521EXAMPLE",
                "State": "available",
                "OwnerId": "123456789012",
                "Description": "MyTGW",
                "CreationTime": "2019-07-10T14:02:12.000Z",
                "Options": {
                    "AmazonSideAsn": 64516,
                    "AutoAcceptSharedAttachments": "enable",
                    "DefaultRouteTableAssociation": "enable",
                    "AssociationDefaultRouteTableId": "tgw-rtb-018774adf3EXAMPLE",
                    "DefaultRouteTablePropagation": "enable",
                    "PropagationDefaultRouteTableId": "tgw-rtb-018774adf3EXAMPLE",
                    "VpnEcmpSupport": "enable",
                    "DnsSupport": "enable"
                },
                "Tags": []
            },
            {
                "TransitGatewayId": "tgw-0fb8421e2dEXAMPLE",
                "TransitGatewayArn": "arn:aws:ec2:us-west-2:123456789012:transit-gateway/tgw-0fb8421e2da853bf3",
                "State": "available",
                "OwnerId": "123456789012",
                "CreationTime": "2019-03-15T22:57:33.000Z",
                "Options": {
                    "AmazonSideAsn": 65412,
                    "AutoAcceptSharedAttachments": "disable",
                    "DefaultRouteTableAssociation": "enable",
                    "AssociationDefaultRouteTableId": "tgw-rtb-06a241a3d8EXAMPLE",
                    "DefaultRouteTablePropagation": "enable",
                    "PropagationDefaultRouteTableId": "tgw-rtb-06a241a3d8EXAMPLE",
                    "VpnEcmpSupport": "enable",
                    "DnsSupport": "enable"
                },
                "Tags": [
                    {
                        "Key": "Name",
                        "Value": "TGW1"
                    }
                ]
            }
        ]
    }

For more information, see `Transit gateways in AWS Transit Gateway <https://docs.aws.amazon.com/vpc/latest/tgw/tgw-transit-gateways.html>`__ in the *Transit Gateways Guide*.
