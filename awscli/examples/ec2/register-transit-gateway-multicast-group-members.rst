**To view the information about the transit gateway multicast domain associations**

This example returns the associations for the specified transit gateway multicast domain. ::

    aws ec2 register-transit-gateway-multicast-group-members \
        --transit-gateway-multicast-domain-id tgw-mcast-domain-0c4905cef79d6e597 \
        --group-ip-address 224.0.1.0 \
        --network-interface-ids eni-0e246d32695012e81

Output::

    {
        "RegisteredMulticastGroupMembers": {
            "TransitGatewayMulticastDomainId": "tgw-mcast-domain-0c4905cef79d6e597",
            "RegisteredNetworkInterfaceIds": [
                "eni-0e246d32695012e81"
            ],
            "GroupIpAddress": "224.0.1.0"
        }
    }

For more information, see `Register Members with a Multicast Group <https://docs.aws.amazon.com/vpc/latest/tgw/working-with-multicast.html#add-members-multicast-group>`__ in the *AWS Transit Gateways User Guide*.
