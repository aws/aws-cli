**To update an outbound security group rule description**

This example updates the description for the security group rule that allows outbound access over port 80 to the ``203.0.113.0/24`` IPv4 address range. The description '``Outbound HTTP access to server 2``' replaces any existing description for the rule. If the command succeeds, no output is returned.

Command::

  aws ec2 update-security-group-rule-descriptions-egress --group-id sg-123abc12 --ip-permissions '[{"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "IpRanges": [{"CidrIp": "203.0.113.0/24", "Description": "Outbound HTTP access to server 2"}]}]'
