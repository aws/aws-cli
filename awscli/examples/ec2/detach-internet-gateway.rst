**To detach an Internet gateway from your VPC**

This example detaches the specified Internet gateway from the specified VPC. If the command succeeds, no output is returned.

Command::

  aws ec2 detach-internet-gateway --internet-gateway-id igw-c0a643a9 --vpc-id vpc-a01106c2
