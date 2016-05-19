**To remove the rule that allows outbound traffic to a specific address range**

This example command removes the rule that grants access to the specified address ranges on TCP port 80.

Command::

  aws ec2 revoke-security-group-egress --group-id sg-1a2b3c4d --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "IpRanges": [{"CidrIp": "10.0.0.0/16"}]}]'

**To remove the rule that allows outbound traffic to a specific security group**

This example command removes the rule that grants access to the specified security group on TCP port 80.

Command::

  aws ec2 revoke-security-group-egress --group-id sg-1a2b3c4d --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "UserIdGroupPairs": [{"GroupId": "sg-4b51a32f"}]}]' 
