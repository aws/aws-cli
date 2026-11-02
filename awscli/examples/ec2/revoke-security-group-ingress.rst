**Example 1: To remove a rule from a security group**

The following ``revoke-security-group-ingress`` example removes TCP port 22 access for the ``203.0.113.0/24`` address range from the specified security group for a default VPC. ::

    aws ec2 revoke-security-group-ingress \
        --group-name mySecurityGroup \
        --protocol tcp \
        --port 22 \
        --cidr 203.0.113.0/24

Output::

    {
        "Return": true,
        "RevokedSecurityGroupRules": [
            {
                "SecurityGroupRuleId": "sgr-0abcdef1234567890",
                "GroupId": "sg-1234567890abcdef0",
                "IsEgress": false,
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "CidrIpv4": "203.0.113.0/24"
            }
        ]
    }

For more information, see `Security groups <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To remove a rule using the IP permissions set**

The following ``revoke-security-group-ingress`` example uses the ``ip-permissions`` parameter to remove an inbound rule that allows the ICMP message ``Destination Unreachable: Fragmentation Needed and Don't Fragment was Set`` (Type 3, Code 4). ::

    aws ec2 revoke-security-group-ingress \
        --group-id sg-026c12253ce15eff7 \
        --ip-permissions IpProtocol=icmp,FromPort=3,ToPort=4,IpRanges=[{CidrIp=0.0.0.0/0}]

Output::

    {
        "Return": true,
        "RevokedSecurityGroupRules": [
            {
                "SecurityGroupRuleId": "sgr-0fedcba9876543210",
                "GroupId": "sg-026c12253ce15eff7",
                "IsEgress": false,
                "IpProtocol": "icmp",
                "FromPort": 3,
                "ToPort": 4,
                "CidrIpv4": "0.0.0.0/0"
            }
        ]
    }

For more information, see `Security groups <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html>`__ in the *Amazon EC2 User Guide*.
