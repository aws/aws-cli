**Example 1: To associate a DHCP options set with your VPC**

The following ``associate-dhcp-options`` example associates the specified DHCP options set with the specified VPC. If the command succeeds, no output is returned. ::

    aws ec2 associate-dhcp-options \
        --dhcp-options-id dopt-d9070ebb \
        --vpc-id vpc-a01106c2

**Example 2: To associate the default DHCP options set with your VPC**

The following ``associate-dhcp-options`` example associates the default DHCP options set with the specified VPC. If the command succeeds, no output is returned. ::

    aws ec2 associate-dhcp-options \
        --dhcp-options-id default \
        --vpc-id vpc-a01106c2
