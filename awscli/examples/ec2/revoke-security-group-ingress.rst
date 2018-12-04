**To remove a rule from a security group**

This example removes TCP port 22 access for the ``203.0.113.0/24`` address range from the security group named ``MySecurityGroup``. If the command succeeds, no output is returned.

Command::

  aws ec2 revoke-security-group-ingress --group-name MySecurityGroup --protocol tcp --port 22 --cidr 203.0.113.0/24

**[EC2-VPC] To remove a rule using the IP permissions set**

This example uses the ``ip-permissions`` parameter to remove an inbound rule that allows the ICMP message ``Destination Unreachable: Fragmentation Needed and Don't Fragment was Set`` (Type 3, Code 4). If the command succeeds, no output is returned. For more information about quoting JSON-formatted parameters, see `Quoting Strings`_.

Command::

  aws ec2 revoke-security-group-ingress --group-id sg-123abc12 --ip-permissions '[{"IpProtocol": "icmp", "FromPort": 3, "ToPort": 4, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]' 

.. _`Quoting Strings`: http://docs.aws.amazon.com/cli/latest/userguide/cli-using-param.html#quoting-strings