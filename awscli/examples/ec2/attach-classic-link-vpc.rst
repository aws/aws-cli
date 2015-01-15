**To link (attach) an EC2-Classic instance to a VPC**

This example links instance i-1a2b3c4d to VPC vpc-88888888 through the VPC security group sg-12312312.

Command::

  aws ec2 attach-classic-link-vpc --instance-id i-1a2b3c4d --vpc-id vpc-88888888 --groups sg-12312312

Output::

  {
    "Return": true
  }