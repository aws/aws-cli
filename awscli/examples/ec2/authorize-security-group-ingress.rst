**[EC2-Classic] To add a rule that allows inbound SSH traffic**

This example enables inbound traffic on TCP port 22 (SSH). If the command succeeds, no output is returned.

Command::

  aws ec2 authorize-security-group-ingress --group-name MySecurityGroup --protocol tcp --port 22 --cidr 203.0.113.0/24

**[EC2-Classic] To add a rule that allows inbound HTTP traffic from a security group in another account**

This example enables inbound traffic on TCP port 80 from a source security group (otheraccountgroup) in a different AWS account (123456789012). Incoming traffic is allowed based on the private IP addresses of instances that are associated with the source security group (not the public IP or Elastic IP addresses). If the command succeeds, no output is returned.

Command::

  aws ec2 authorize-security-group-ingress --group-name MySecurityGroup --protocol tcp --port 80 --source-group otheraccountgroup --group-owner 123456789012

**[EC2-Classic] To add a rule that allows inbound HTTPS traffic from an ELB**

This example enables inbound traffic on TCP port 443 from an ELB. If the command succeeds, no output is returned.

Command::

  aws ec2 authorize-security-group-ingress --group-name MySecurityGroup --protocol tcp --port 443 --source-group amazon-elb-sg --group-owner amazon-elb

**[EC2-VPC] To add a rule that allows inbound SSH traffic**

This example enables inbound traffic on TCP port 22 (SSH). Note that you can't reference a security group for EC2-VPC by name. If the command succeeds, no output is returned.

Command::

  aws ec2 authorize-security-group-ingress --group-id sg-903004f8 --protocol tcp --port 22 --cidr 203.0.113.0/24

**[EC2-VPC] To add a rule that allows inbound HTTP traffic from another security group**

This example enables inbound access on TCP port 80 from the source security group sg-1a2b3c4d. Note that for EC2-VPC, the source group must be in the same VPC or in a peer VPC (requires a VPC peering connection). Incoming traffic is allowed based on the private IP addresses of instances that are associated with the source security group (not the public IP or Elastic IP addresses). If the command succeeds, no output is returned.

Command::

  aws ec2 authorize-security-group-ingress --group-id sg-111aaa22 --protocol tcp --port 80 --source-group sg-1a2b3c4d

**[EC2-VPC] To add two rules, one for RDP and another for ping/ICMP**

This example uses the ``ip-permissions`` parameter to add two rules, one that enables inbound access on TCP port 3389 (RDP) and the other that enables ping/ICMP.

Command (Windows)::

  aws ec2 authorize-security-group-ingress --group-id sg-1a2b3c4d --ip-permissions IpProtocol=tcp,FromPort=3389,ToPort=3389,IpRanges=[{CidrIp=172.31.0.0/16}] IpProtocol=icmp,FromPort=-1,ToPort=-1,IpRanges=[{CidrIp=172.31.0.0/16}]
  
**[EC2-VPC] To add a custom ICMP rule**

This example uses the ``ip-permissions`` parameter to add an inbound rule that allows the ICMP message ``Destination Unreachable: Fragmentation Needed and Don't Fragment was Set`` (Type 3, Code 4) from anywhere. If the command succeeds, no output is returned. For more information about quoting JSON-formatted parameters, see `Quoting Strings`_.

Command (Linux)::

  aws ec2 authorize-security-group-ingress --group-id sg-123abc12 --ip-permissions IpProtocol=icmp,FromPort=3,ToPort=4,IpRanges='[{CidrIp=0.0.0.0/0}]' 

Command (Windows)::

  aws ec2 authorize-security-group-ingress --group-id sg-123abc12 --ip-permissions IpProtocol=icmp,FromPort=3,ToPort=4,IpRanges=[{CidrIp=0.0.0.0/0}]

**[EC2-VPC] To add a rule for IPv6 traffic**

This example grants SSH access (port 22) from the IPv6 range ``2001:db8:1234:1a00::/64``.

Command (Linux)::

  aws ec2 authorize-security-group-ingress --group-id sg-9bf6ceff --ip-permissions IpProtocol=tcp,FromPort=22,ToPort=22,Ipv6Ranges='[{CidrIpv6=2001:db8:1234:1a00::/64}]'

Command (Windows)::

  aws ec2 authorize-security-group-ingress --group-id sg-9bf6ceff --ip-permissions IpProtocol=tcp,FromPort=22,ToPort=22,Ipv6Ranges=[{CidrIpv6=2001:db8:1234:1a00::/64}]

**Add a rule with a description**

This example uses the ``ip-permissions`` parameter to add an inbound rule that allows RDP traffic from a specific IPv4 address range. The rule includes a description to help you identify it later.

Command (Linux)::

  aws ec2 authorize-security-group-ingress --group-id sg-123abc12 --ip-permissions IpProtocol=tcp,FromPort=3389,ToPort=3389,IpRanges='[{CidrIp=203.0.113.0/24,Description="RDP access from NY office"}]'

Command (Windows)::

  aws ec2 authorize-security-group-ingress --group-id sg-123abc12 --ip-permissions IpProtocol=tcp,FromPort=3389,ToPort=3389,IpRanges=[{CidrIp=203.0.113.0/24,Description="RDP access from NY office"}]

For more information, see `Using Security Groups`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Security Groups`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html
