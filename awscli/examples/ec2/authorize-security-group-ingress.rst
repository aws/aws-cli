**To add a rule to a security group that allow inbound SSH traffic**

This example enables inbound traffic on TCP port 22 (SSH).

Command::

  aws ec2 authorize-security-group-ingress --group-name MySecurityGroup --protocol tcp --port 22 --cidr 203.0.113.0/24

Output::

  {
      "SecurityGroups": [
          {
              "IpPermissionsEgress": [],
              "Description": "My security group"
              "IpPermissions": [
                  {
                      "ToPort": 22,
                      "IpProtocol": "tcp",
                      "IpRanges": [
                          {
                              "CidrIp": "203.0.113.0/24"
                          }
                      ]
                      "UserIdGroupPairs": [],
                      "FromPort": 22
                  }
              ],
              "GroupName": "MySecurityGroup",
              "OwnerId": "123456789012",
              "GroupId": "sg-903004f8"
          }
      ]
  }

For more information, see `Using Security Groups`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Security Groups`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html

