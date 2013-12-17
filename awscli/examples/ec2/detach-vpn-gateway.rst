**To detach a virtual private gateway from your VPC**

This example detaches the specified virtual private gateway from the specified VPC.

Command::

  aws ec2 detach-internet-gateway --vpn-gateway-id vgw-9a4cacf3 --vpc-id vpc-a01106c2

Output::

  {
      "return": "true"
  }