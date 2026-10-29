**To delete a static route from a VPN connection**

The following ``delete-vpn-connection-route`` example deletes the specified static route from the specified VPN connection. ::

    aws ec2 delete-vpn-connection-route \
        --vpn-connection-id vpn-40f41529 \
        --destination-cidr-block 11.12.0.0/16

This command produces no output.

For more information, see `AWS Site-to-Site VPN routing options <https://docs.aws.amazon.com/vpn/latest/s2svpn/VPNRoutingTypes.html>`__ in the *AWS Site-to-Site VPN User Guide*.
