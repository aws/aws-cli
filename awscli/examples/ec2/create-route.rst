**To create a route**

This example creates a route for the specified route table. The route matches all traffic (``0.0.0.0/0``) and routes it to the specified Internet gateway.

Command::

  aws ec2 create-route --route-table-id rtb-22574640 --destination-cidr-block 0.0.0.0/0 --gateway-id igw-c0a643a9

Output::

  {
      "return": "true"
  }