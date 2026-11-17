**To replace the network ACL associated with a subnet**

The following ``replace-network-acl-association`` example associates the specified network ACL with the subnet for the specified network ACL association. ::

    aws ec2 replace-network-acl-association \
        --association-id aclassoc-e5b95c8c \
        --network-acl-id acl-5fb85d36

Output::

    {
        "NewAssociationId": "aclassoc-3999875b"
    }

For more information, see `Control subnet traffic with network access control lists <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html>`__ in the *Amazon VPC User Guide*.
