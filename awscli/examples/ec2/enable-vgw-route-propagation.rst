**To enable route propagation**

This example enables the specified virtual private gateway to propagate static routes to the specified route table.

Command::

  aws ec2 enable-vgw-route-propagation --route-table-id rtb-22574640 --gateway-id vgw-9a4cacf3

Output::

  {
      "return": "true"
  }