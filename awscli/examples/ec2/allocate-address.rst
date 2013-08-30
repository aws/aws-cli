**To allocate an Elastic IP address for EC2-Classic**

This example allocates an Elastic IP address to use with an instance in EC2-Classic.

Command::

  aws ec2 allocate-address

Output::

  {
      "PublicIp": "198.51.100.0",
      "Domain": "standard"
  }

**To allocate an Elastic IP address for EC2-VPC**

This example allocates an Elastic IP address to use with an instance in a VPC.

Command::

  aws ec2 allocate-address --domain vpc

Output::

  {
      "PublicIp": "203.0.113.0",
      "Domain": "vpc",
      "AllocationId": "eipalloc-64d5890a"
  }

