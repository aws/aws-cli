**To delete a transit gateway multicast domain**

This example returns the route table propagations for the specified route table.::

    aws ec2 delete-transit-gateway-multicast-domain \
        --transit-gateway-multicast-domain-id tgw-mcast-domain-0c4905cef7EXAMPLE

Output::

    {
        "TransitGatewayMulticastDomain": {
            "TransitGatewayMulticastDomainId": "tgw-mcast-domain-02bb79002bEXAMPLE",
            "TransitGatewayId": "tgw-0d88d2d0d5EXAMPLE",
            "State": "deleting",
            "CreationTime": "2019-11-20T22:02:03.000Z"
        }
    }

For more information, see 'Delete a Transit Gateway Multicast Domain<https://docs.aws.amazon.com/vpc/latest/tgw/tgw-route-tables.html#view-tgw-route-propagations>'__ in the *AWS Transit Gateways User Guide*.
