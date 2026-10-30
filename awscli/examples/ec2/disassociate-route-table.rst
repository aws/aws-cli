**To disassociate a route table**

The following ``disassociate-route-table`` example disassociates the specified route table from the specified subnet. ::

    aws ec2 disassociate-route-table \
        --association-id rtbassoc-781d0d1a

This command produces no output.

For more information, see `Change the route table for a subnet <https://docs.aws.amazon.com/vpc/latest/userguide/WorkWithRouteTables.html#ChangeRouteTable>`__ in the *Amazon VPC User Guide*.
