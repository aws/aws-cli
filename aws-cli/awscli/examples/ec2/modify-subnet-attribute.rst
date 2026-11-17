**Example 1: To change a subnet's public IPv4 addressing behavior**

The following ``modify-subnet-attribute`` example modifies subnet-1a2b3c4d to specify that all instances launched into this subnet are assigned a public IPv4 address. ::

    aws ec2 modify-subnet-attribute \
        --subnet-id subnet-1a2b3c4d \
        --map-public-ip-on-launch

This command produces no output.

For more information, see `Modify the IP addressing attributes of your subnet <https://docs.aws.amazon.com/vpc/latest/userguide/subnet-public-ip.html>`__ in the *Amazon VPC User Guide*.

**Example 2: To change a subnet's IPv6 addressing behavior**

The following ``modify-subnet-attribute`` example modifies subnet-1a2b3c4d to specify that all instances launched into this subnet are assigned an IPv6 address from the range of the subnet. ::

    aws ec2 modify-subnet-attribute \
        --subnet-id subnet-1a2b3c4d \
        --assign-ipv6-address-on-creation

This command produces no output.

For more information, see `IP addressing for your VPCs and subnets <https://docs.aws.amazon.com/vpc/latest/userguide/vpc-ip-addressing.html>`__ in the *Amazon VPC User Guide*.
