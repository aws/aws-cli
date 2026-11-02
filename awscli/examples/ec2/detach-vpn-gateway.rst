**To detach a virtual private gateway from your VPC**

The following ``detach-vpn-gateway`` example detaches the specified virtual private gateway from the specified VPC. ::

    aws ec2 detach-vpn-gateway \
        --vpn-gateway-id vgw-9a4cacf3 \
        --vpc-id vpc-a01106c2

This command produces no output.

For more information, see `How AWS Site-to-Site VPN works <https://docs.aws.amazon.com/vpn/latest/s2svpn/how_it_works.html>`__ in the *AWS Site-to-Site VPN User Guide*.
