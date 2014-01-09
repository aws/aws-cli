**To disable route propagation**

This example disables the specified virtual private gateway from propagating static routes to the specified route table.

Command::

  aws ec2 disable-vgw-route-propagation --route-table-id rtb-22574640 --gateway-id vgw-9a4cacf3

Output::

  {
      "return": "true"
  }