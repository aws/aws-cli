**Example 1: [EC2-Classic] To add a rule that allows inbound SSH traffic**

The following example enables inbound traffic on TCP port 22 (SSH). If the command succeeds, no output is returned. ::

    aws ec2 authorize-security-group-ingress \
        --group-name MySecurityGroup \
        --protocol tcp \
        --port 22 \
        --cidr 203.0.113.0/24

This command produces no output.

**Example 2: [EC2-Classic] To add a rule that allows inbound HTTP traffic from a security group in another account**

The following example enables inbound traffic on TCP port 80 from a source security group (``otheraccountgroup``) in a different AWS account (123456789012). Incoming traffic is allowed based on the private IP addresses of instances that are associated with the source security group (not the public IP or Elastic IP addresses). ::

    aws ec2 authorize-security-group-ingress \
        --group-name MySecurityGroup \
        --protocol tcp \
        --port 80 \
        --source-group otheraccountgroup \
        --group-owner 123456789012

This command produces no output.

**Example 3: [EC2-Classic] To add a rule that allows inbound HTTPS traffic from an ELB**

The following example enables inbound traffic on TCP port 443 from an ELB. ::

    aws ec2 authorize-security-group-ingress \
        --group-name MySecurityGroup \
        --protocol tcp \
        --port 443 \
        --source-group amazon-elb-sg \
        --group-owner amazon-elb

**Example 4: [EC2-VPC] To add a rule that allows inbound SSH traffic**

The following example enables inbound traffic on TCP port 22 (SSH). Note that you can't reference a security group for EC2-VPC by name. ::

    aws ec2 authorize-security-group-ingress \
        --group-id sg-1234567890abcdef0 \
        --protocol tcp \
        --port 22 \
        --cidr 203.0.113.0/24

This command produces no output.

**Example 5: [EC2-VPC] To add a rule that allows inbound HTTP traffic from another security group**

The following example enables inbound access on TCP port 80 from the source security group ``sg-1a2b3c4d``. Note that for EC2-VPC, the source group must be in the same VPC or in a peer VPC (requires a VPC peering connection). Incoming traffic is allowed based on the private IP addresses of instances that are associated with the source security group (not the public IP or Elastic IP addresses). ::

    aws ec2 authorize-security-group-ingress \
        --group-id sg-1234567890abcdef0 \
        --protocol tcp \
        --port 80 \
        --source-group sg-1a2b3c4d

This command produces no output.

**Example 6: [EC2-VPC] To add one rule for RDP and another rule for ping/ICMP**

The following example uses the ``ip-permissions`` parameter to add two rules, one that enables inbound access on TCP port 3389 (RDP) and the other that enables ping/ICMP.  

Windows::

    aws ec2 authorize-security-group-ingress ^
        --group-id sg-1234567890abcdef0 ^
        --ip-permissions IpProtocol=tcp,FromPort=3389,ToPort=3389,IpRanges=[{CidrIp=172.31.0.0/16}] IpProtocol=icmp,FromPort=-1,ToPort=-1,IpRanges=[{CidrIp=172.31.0.0/16}]
  
**Example 7: [EC2-VPC] To add a rule for ICMP traffic**

The following example uses the ``ip-permissions`` parameter to add an inbound rule that allows the ICMP message ``Destination Unreachable: Fragmentation Needed and Don't Fragment was Set`` (Type 3, Code 4) from anywhere.

Linux::

    aws ec2 authorize-security-group-ingress \
        --group-id sg-1234567890abcdef0 \
        --ip-permissions IpProtocol=icmp,FromPort=3,ToPort=4,IpRanges='[{CidrIp=0.0.0.0/0}]'

Windows::

    aws ec2 authorize-security-group-ingress ^
        --group-id sg-1234567890abcdef0 ^
        --ip-permissions IpProtocol=icmp,FromPort=3,ToPort=4,IpRanges=[{CidrIp=0.0.0.0/0}]

This command produces no output. 

**Example 8: [EC2-VPC] To add a rule for IPv6 traffic**

The following example grants SSH access (port 22) from the IPv6 range ``2001:db8:1234:1a00::/64``.  

Linux::

    aws ec2 authorize-security-group-ingress \
        --group-id sg-1234567890abcdef0 \
        --ip-permissions IpProtocol=tcp,FromPort=22,ToPort=22,Ipv6Ranges='[{CidrIpv6=2001:db8:1234:1a00::/64}]'

Windows::

    aws ec2 authorize-security-group-ingress ^
        --group-id sg-1234567890abcdef0 ^
        --ip-permissions IpProtocol=tcp,FromPort=22,ToPort=22,Ipv6Ranges=[{CidrIpv6=2001:db8:1234:1a00::/64}]

**Example 9: [EC2-VPC] To add a rule for ICMPv6 traffic**

The following example uses the ``ip-permissions`` parameter to add an inbound rule that allows ICMPv6 traffic from anywhere.  

Linux::

    aws ec2 authorize-security-group-ingress \
        --group-id sg-1234567890abcdef0 \
        --ip-permissions IpProtocol=icmpv6,Ipv6Ranges='[{CidrIpv6=::/0}]'   
    
Windows::

    aws ec2 authorize-security-group-ingress ^
        --group-id sg-1234567890abcdef0 ^
        --ip-permissions IpProtocol=icmpv6,Ipv6Ranges=[{CidrIpv6=::/0}]
		
**Example 10: [EC2-VPC] To add an inbound rule that uses a prefix list**

A prefix list is a set of one or more CIDR blocks. You can use prefix lists with security group rules to allow connections from IP addresses that fall within the CIDR block ranges in a prefix list. The following example uses the ``ip-permissions`` parameter to add an inbound rule for all CIDR ranges in a specific prefix list on port 22.  

Linux::

    aws ec2 authorize-security-group-ingress \
        --group-id sg-04a351bfe432d4e71 \
        --ip-permissions IpProtocol=all,FromPort=22,ToPort=22,PrefixListIds=[{PrefixListId=pl-002dc3ec097de1514}]
        
Windows::

    aws ec2 authorize-security-group-ingress ^
        --group-id sg-04a351bfe432d4e71 ^
        --ip-permissions IpProtocol=all,FromPort=22,ToPort=22,PrefixListIds=[{PrefixListId=pl-002dc3ec097de1514}]
        
**Example 11: Add a rule with a description**

The following example uses the ``ip-permissions`` parameter to add an inbound rule that allows RDP traffic from a specific IPv4 address range. The rule includes a description to help you identify it later.  

Linux::

    aws ec2 authorize-security-group-ingress \
        --group-id sg-1234567890abcdef0 \
        --ip-permissions IpProtocol=tcp,FromPort=3389,ToPort=3389,IpRanges='[{CidrIp=203.0.113.0/24,Description="RDP access from NY office"}]'
        
Windows::

    aws ec2 authorize-security-group-ingress ^
        --group-id sg-1234567890abcdef0 ^
        --ip-permissions IpProtocol=tcp,FromPort=3389,ToPort=3389,IpRanges=[{CidrIp=203.0.113.0/24,Description="RDP access from NY office"}]

For more information, see `Using Security Groups`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Security Groups`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html