**To view information about a security group**

The following example uses the ``describe-security-groups`` command to view information about a previously created security group named MySecurityGroup::

    aws ec2 describe-security-groups --group-names MySecurityGroup

Output::

  {
      "securityGroupInfo": [
          {
              "ipPermissionsEgress": [],
              "groupId": "sg-903004f8",
              "ipPermissions": [],
              "groupName": "MySecurityGroup",
              "ownerId": "803981987763",
              "groupDescription": "AWS-CLI-Example"
          }
      ],
      "requestId": "afb680df-d7b1-4f6a-b1a7-344fdb1e3532"
  }

For more information, see `Amazon EC2 Security Groups`_ in the *AWS Command Line Interface User Guide*.

.. _Amazon EC2 Security Groups: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html

