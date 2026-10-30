**To disassociate a route table**

The following ``disassociate-route-table`` example disassociates the specified route table from the specified subnet. If the command succeeds, no output is returned. ::

    aws ec2 disassociate-route-table \
        --association-id rtbassoc-781d0d1a
