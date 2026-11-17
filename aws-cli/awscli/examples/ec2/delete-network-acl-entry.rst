**To delete a network ACL entry**

The following ``delete-network-acl-entry`` example deletes ingress rule number 100 from the specified network ACL. ::

    aws ec2 delete-network-acl-entry \
        --network-acl-id acl-5fb85d36 \
        --ingress \
        --rule-number 100

This command produces no output.

For more information, see `Network ACL rules <https://docs.aws.amazon.com/vpc/latest/userguide/nacl-rules.html>`__ in the *Amazon VPC User Guide*.
