**To unassign an IPv6 address from a network interface**

The following ``unassign-ipv6-addresses`` example unassigns the specified IPv6 address from the specified network interface. ::

    aws ec2 unassign-ipv6-addresses \
        --ipv6-addresses 2001:db8:1234:1a00:3304:8879:34cf:4071 \
        --network-interface-id eni-23c49b68

Output::

    {
        "NetworkInterfaceId": "eni-23c49b68",
        "UnassignedIpv6Addresses": [
            "2001:db8:1234:1a00:3304:8879:34cf:4071"
        ]
    }

For more information, see `Manage the IPv6 addresses for your EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/working-with-ipv6-addresses.html>`__ in the *Amazon EC2 User Guide*.
