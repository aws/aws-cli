**To display information about a security group for EC2-Classic**

This example displays information about the security group named ``MySecurityGroup``.

Command::

  aws ec2 describe-security-groups --group-names MySecurityGroup

Output::

  {
      "SecurityGroups": [
          {
              "IpPermissionsEgress": [],
              "Description": "My security group",
              "IpPermissions": [
                  {
                      "ToPort": 22,
                      "IpProtocol": "tcp",
                      "IpRanges": [
                          {
                              "CidrIp": "203.0.113.0/24"
                          }
                      ],
                      "UserIdGroupPairs": [],
                      "FromPort": 22
                  }
              ],
              "GroupName": "MySecurityGroup",
              "OwnerId": "123456789012",
              "GroupId": "sg-903004f8",
          }
      ]
  }

**To display information about a security group for EC2-VPC**

This example displays information about the security group with the ID sg-903004f8. Note that you can't reference a security group for EC2-VPC by name.

Command::

  aws ec2 describe-security-groups --group-ids sg-903004f8

Output::

  {
      "SecurityGroups": [
          {
              "IpPermissionsEgress": [
                  {
                      "IpProtocol": "-1",
                      "IpRanges": [
                          {
                              "CidrIp": "0.0.0.0/0"
                          }
                      ],
                      "UserIdGroupPairs": []
                  }
              ],
              "Description": "My security group",
              "IpPermissions": [
                  {
                      "ToPort": 22,
                      "IpProtocol": "tcp",
                      "IpRanges": [
                          {
                              "CidrIp": "203.0.113.0/24"
                          }
                      ],
                      "UserIdGroupPairs": [],
                      "FromPort": 22
                  }
              ],
              "GroupName": "MySecurityGroup",
              "VpcId": "vpc-1a2b3c4d",
              "OwnerId": "123456789012",
              "GroupId": "sg-903004f8",
          }
      ]
  }

For more information, see `Using Security Groups`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Security Groups`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html

