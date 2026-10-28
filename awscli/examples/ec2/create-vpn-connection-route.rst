**To create a static route for a VPN connection**

The following ``create-vpn-connection-route`` example creates a static route for the specified VPN connection. If the command succeeds, no output is returned. ::

    aws ec2 create-vpn-connection-route \
        --vpn-connection-id vpn-40f41529 \
        --destination-cidr-block 11.12.0.0/16
