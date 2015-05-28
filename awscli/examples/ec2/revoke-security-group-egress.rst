**To remove the rule that allows outbound traffic to a specific address range**

This example command removes the rule that grants access to the specified address ranges on TCP port 80.

Command:

  aws ec2 revoke-security-group-egress --group-id sg-1a2b3c4d --protocol tcp --port 80 --cidr 203.0.113.0/24

**To remove the rule that allows outbound traffic to a specific security group**

This example command removes the rule that grants access to the specified security group on TCP port 80.

Command:

  aws ec2 revoke-security-group-egress --group-id sg-1a2b3c4d --protocol tcp --port 80 --source-group sg-9a8d7f5c
