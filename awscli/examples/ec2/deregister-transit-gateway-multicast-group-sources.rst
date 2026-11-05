**To deregister a source from the transit gateway multicast group**

The following ``deregister-transit-gateway-multicast-group-sources`` example deregisters the specified network interface group source from the multicast group. ::

    aws ec2 deregister-transit-gateway-multicast-group-sources \
        --transit-gateway-multicast-domain-id tgw-mcast-domain-0c4905cef79d6e597 \
        --group-ip-address 224.0.1.0 \
        --network-interface-ids eni-07f290fc3c090cbae 

Output::

    {
        "DeregisteredMulticastGroupSources": {
            "TransitGatewayMulticastDomainId": "tgw-mcast-domain-0c4905cef79d6e597",
            "DeregisteredNetworkInterfaceIds": [
                "eni-07f290fc3c090cbae"
            ],
            "GroupIpAddress": "224.0.1.0"
        }
    }

For more information, see `Deregister sources from a multicast group in AWS Transit Gateway <https://docs.aws.amazon.com/vpc/latest/tgw/remove-source-multicast-group.html>`__ in the *AWS Transit Gateways User Guide*.
