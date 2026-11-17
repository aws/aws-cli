**To replace the route table associated with a subnet**

The following ``replace-route-table-association`` example associates the specified route table with the subnet for the specified route table association. ::

    aws ec2 replace-route-table-association \
        --association-id rtbassoc-781d0d1a \
        --route-table-id rtb-22574640

Output::

    {
        "NewAssociationId": "rtbassoc-3a1f0f58"
    }

For more information, see `Manage subnet route tables <https://docs.aws.amazon.com/vpc/latest/userguide/WorkWithRouteTables.html>`__ in the *Amazon VPC User Guide*.
