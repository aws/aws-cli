**To view information about a security group**

The following example uses the ``describe-security-groups`` command to view information about the security group named WebServerSG::

    aws ec2 describe-security-groups --group-names WebServerSG

The output of this command is a JSON block that describes the security group, similar to the following::

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
              "Description": "For web servers",
              "IpPermissions": [
                  {
                      "ToPort": 80,
                      "IpProtocol": "tcp",
                      "IpRanges": [
                          {
                              "CidrIp": "0.0.0.0/0"
                          }
                      ],
                      "UserIdGroupPairs": [],
                      "FromPort": 80
                  },
                  {
                      "ToPort": 443,
                      "IpProtocol": "tcp",
                      "IpRanges": [
                          {
                              "CidrIp": "0.0.0.0/0"
                          }
                      ],
                      "UserIdGroupPairs": [],
                      "FromPort": 443
                  },              
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
              "GroupName": "WebServerSG",
              "VpcId": "vpc-44eb7ef7"
              "OwnerId": "803981987763",
              "GroupId": "sg-903004f8",              
          }
      ],
      "ResponseMetadata": {
          "RequestId": "afb680df-d7b1-4f6a-b1a7-344fdb1e3532"
      }
  }

For more information, see `Using Security Groups`_ in the *AWS Command Line Interface User Guide*.

.. _Using Security Groups: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html

