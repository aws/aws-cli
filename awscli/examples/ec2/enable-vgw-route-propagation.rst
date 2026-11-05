**To enable route propagation**

The following ``enable-vgw-route-propagation`` example enables the specified virtual private gateway to propagate static routes to the specified route table. ::

    aws ec2 enable-vgw-route-propagation \
        --route-table-id rtb-22574640 \
        --gateway-id vgw-9a4cacf3

This command produces no output.

For more information, see `Manage subnet route tables <https://docs.aws.amazon.com/vpc/latest/userguide/WorkWithRouteTables.html#EnableDisableRouteProp>`__ in the *Amazon VPC User Guide*.
