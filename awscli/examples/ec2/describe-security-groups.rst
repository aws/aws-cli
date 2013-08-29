**To display information about a security group**

This example displays information about the security group named MySecurityGroup.

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

For more information, see `Using Security Groups`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Security Groups`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html

