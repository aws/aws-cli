**To unlink (detach) an EC2-Classic instance from a VPC**

This example unlinks instance i-1a2b3c4d from VPC vpc-88888888.

Command::

  aws ec2 detach-classic-link-vpc --instance-id i-1a2b3c4d --vpc-id vpc-88888888

Output::

  {
    "Return": true
  }