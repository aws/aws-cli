**To attach an Internet gateway to your VPC**

This example attaches the specified Internet gateway to the specified VPC.

Command::

  aws ec2 attach-internet-gateway --internet-gateway-id igw-c0a643a9 --vpc-id vpc-a01106c2

Output::

  {
      "return": "true"
  }