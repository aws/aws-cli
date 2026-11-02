**To delete a route**

The following ``delete-route`` example deletes the specified route from the specified route table. ::

    aws ec2 delete-route \
        --route-table-id rtb-22574640 \
        --destination-cidr-block 0.0.0.0/0

This command produces no output.

For more information, see `Add, modify, and remove routes <https://docs.aws.amazon.com/vpc/latest/userguide/WorkWithRouteTables.html#AddRemoveRoutes>`__ in the *Amazon VPC User Guide*.
