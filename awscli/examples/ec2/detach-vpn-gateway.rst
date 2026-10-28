**To detach a virtual private gateway from your VPC**

The following ``detach-vpn-gateway`` example detaches the specified virtual private gateway from the specified VPC. This command produces no output. ::

    aws ec2 detach-vpn-gateway \
        --vpn-gateway-id vgw-9a4cacf3 \
        --vpc-id vpc-a01106c2
