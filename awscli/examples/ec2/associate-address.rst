**To associate an Elastic IP addresses in EC2-Classic**

This example associates an Elastic IP address with an instance in EC2-Classic.

Command::

  aws ec2 associate-address --instance-id i-5203422c --public-ip 198.51.100.0

Output::

  {
      "return": "true"
  }

**To associate an Elastic IP address in EC2-VPC**

This example associates an Elastic IP address with an instance in a VPC.

Command::

  aws ec2 associate-address --instance-id i-43a4412a --allocation-id eipalloc-64d5890a

Output::

  {
      "AssociationId": "eipassoc-2bebb745",
      "return": "true"
  }

