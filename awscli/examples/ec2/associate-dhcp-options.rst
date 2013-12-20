**To associate a DHCP options set with your VPC**

This example associates the specified DHCP options set with the specified VPC.

Command::

  aws ec2 associate-dhcp-options --dhcp-options-id dopt-d9070ebb --vpc-id vpc-a01106c2

Output::

  {
      "return": "true"
  }

**To associate the default DHCP options set with your VPC**

This example associates the default DHCP options set with the specified VPC.

Command::

  aws ec2 associate-dhcp-options --dhcp-options-id default --vpc-id vpc-a01106c2

Output::

  {
      "return": "true"
  }