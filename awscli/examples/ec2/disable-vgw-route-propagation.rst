**To disable route propagation**

The following ``disable-vgw-route-propagation`` example disables the specified virtual private gateway from propagating static routes to the specified route table. ::

    aws ec2 disable-vgw-route-propagation \
        --route-table-id rtb-22574640 \
        --gateway-id vgw-9a4cacf3

This command produces no output.
