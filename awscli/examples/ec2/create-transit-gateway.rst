**To create a transit gateway**

The following ``create-transit-gateway`` example creates a transit gateway. ::

    aws ec2 create-transit-gateway \
        --description MyTGW \
        --options AmazonSideAsn=64516,AutoAcceptSharedAttachments=enable,DefaultRouteTableAssociation=enable,DefaultRouteTablePropagation=enable,VpnEcmpSupport=enable,DnsSupport=enable

Output::

    {
        "TransitGateway": {
            "TransitGatewayId": "tgw-0262a0e521EXAMPLE",
            "TransitGatewayArn": "arn:aws:ec2:us-west-2:123456789012:transit-gateway/tgw-0262a0e521EXAMPLE",
            "State": "pending",
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
            }
        }
    }

For more information, see `Create a transit gateway <https://docs.aws.amazon.com/vpc/latest/tgw/create-tgw.html>`__ in the *Transit Gateways Guide*.