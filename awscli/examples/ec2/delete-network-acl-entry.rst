**To delete a network ACL entry**

This example deletes ingress rule number 100 from the specified network ACL.

Command::

  aws ec2 delete-network-acl-entry --network-acl-id acl-5fb85d36 --ingress --rule-number 100

Output::

  {
      "return": "true"
  }