**To create a static route for a VPN connection**

The following ``create-vpn-connection-route`` example creates a static route for the specified VPN connection. ::

    aws ec2 create-vpn-connection-route \
        --vpn-connection-id vpn-40f41529 \
        --destination-cidr-block 11.12.0.0/16

This command produces no output.

For more information, see `AWS Site-to-Site VPN routing options <https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html>`__ in the *AWS Site-to-Site VPN User Guide*.
