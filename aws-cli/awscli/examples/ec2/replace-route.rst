**To replace a route**

The following ``replace-route`` example replaces the specified route in the specified route table. The new route matches the specified CIDR and sends the traffic to the specified virtual private gateway. ::

    aws ec2 replace-route \
        --route-table-id rtb-22574640 \
        --destination-cidr-block 10.0.0.0/16 \
        --gateway-id vgw-9a4cacf3

This command produces no output.

For more information, see `Manage subnet route tables <https://docs.aws.amazon.com/vpc/latest/userguide/WorkWithRouteTables.html>`__ in the *Amazon VPC User Guide*.
