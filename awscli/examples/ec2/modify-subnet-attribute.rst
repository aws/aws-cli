**To change a subnet's public IP addressing behavior**

This example modifies subnet-1a2b3c4d to specify that all instances launched into this subnet are assigned a public IP address. If the command succeeds, no output is returned.

Command::

  aws ec2 modify-subnet-attribute --subnet-id subnet-1a2b3c4d --map-public-ip-on-launch

For more information, see `IP Addressing in Your VPC`_ in the *AWS Virtual Private Cloud User Guide*.

.. _`IP Addressing in Your VPC`: http://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/vpc-ip-addressing.html