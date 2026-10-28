**To delete a static route from a VPN connection**

The following ``delete-vpn-connection-route`` example deletes the specified static route from the specified VPN connection. If the command succeeds, no output is returned. ::

    aws ec2 delete-vpn-connection-route --vpn-connection-id vpn-40f41529 --destination-cidr-block 11.12.0.0/16
