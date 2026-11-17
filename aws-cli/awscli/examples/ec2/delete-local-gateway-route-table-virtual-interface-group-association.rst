**To disassociate a local gateway route table from a virtual interfaces (VIFs) group**

The following ``delete-local-gateway-route-table-virtual-interface-group-association`` example deletes the association between the specified local gateway route table and VIF group. ::

    aws ec2 delete-local-gateway-route-table-virtual-interface-group-association \
        --local-gateway-route-table-virtual-interface-group-association-id lgw-vif-grp-assoc-exampleid12345678

Output::

    {
        "LocalGatewayRouteTableVirtualInterfaceGroupAssociation": {
            "LocalGatewayRouteTableVirtualInterfaceGroupAssociationId": "lgw-vif-grp-assoc-exampleid12345678",
            "LocalGatewayVirtualInterfaceGroupId": "lgw-vif-grp-exampleid0123abcd",
            "LocalGatewayId": "lgw-exampleid11223344",
            "LocalGatewayRouteTableId": "lgw-rtb-exampleidabcd1234",
            "LocalGatewayRouteTableArn": "arn:aws:ec2:us-west-2:123456789012:local-gateway-route-table/lgw-rtb-exampleidabcd1234",
            "OwnerId": "123456789012",
            "State": "disassociating",
            "Tags": []
        }
    }

For more information, see `VIF group associations <https://docs.aws.amazon.com/outposts/latest/userguide/routing.html>`__ in the *AWS Outposts User Guide*.