**To update an inbound security group rule description**

This example updates the description for the security group rule that allows inbound access over port 22 from the ``203.0.113.0/16`` IPv4 address range. The description '``SSH access from ABC office``' replaces any existing description for the rule. If the command succeeds, no output is returned.

Command::

  aws ec2 update-security-group-rule-descriptions-ingress --group-id sg-123abc12 --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "203.0.113.0/16", "Description": "SSH access from ABC office"}]}]'
