**To release an Elastic IP addresses for EC2-Classic**

This example releases an Elastic IP address for use with instances in EC2-Classic.

Command::

  aws ec2 release-address --public-ip 198.51.100.0

Output::

  {
      "return": "true"
  }

**To release an Elastic IP address for EC2-VPC**

This example releases an Elastic IP address for use with instances in a VPC.

Command::

  aws ec2 release-address --allocation-id eipalloc-64d5890a

Output::

  {
      "return": "true"
  }

