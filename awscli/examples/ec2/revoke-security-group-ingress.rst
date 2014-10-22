**To remove a rule from a security group**

This example removes TCP port 22 access for the ``203.0.113.0/24`` address range from the security group named ``MySecurityGroup``. If the command succeeds, no output is returned.

Command::

  aws ec2 revoke-security-group-ingress --group-name MySecurityGroup --protocol tcp --port 22 --cidr 203.0.113.0/24
