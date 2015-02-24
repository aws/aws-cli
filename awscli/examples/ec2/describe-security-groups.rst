**To describe a security group for EC2-Classic**

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

**To describe a security group for EC2-VPC**

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

**To describe security groups that have a specific rule**

(EC2-VPC only) This example uses filters to describe security groups that have a rule that allows SSH traffic (port 22) from all IP addresses (``0.0.0.0/0``). The output is filtered to display only the names of the security groups.

Command::

  aws ec2 describe-security-groups --filters Name=ip-permission.from-port,Values=22 Name=ip-permission.to-port,Values=22 Name=ip-permission.cidr,Values='0.0.0.0/0' --query 'SecurityGroups[*].{Name:GroupName}'

Output::

   [
     {
        "Name": "default"
     }, 
     {
        "Name": "Test SG"
     }, 
     {
        "Name": "SSH-Access-Group"
     }
   ]

**To describe tagged security groups**

This example describes all security groups that include ``test`` in the security group name, and that have the tag ``Test=To-delete``. The output is filtered to display only the names and IDs of the security groups.

Command::

  aws ec2 describe-security-groups --filters Name=group-name,Values='*test*' Name=tag-key,Values=Test Name=tag-value,Values=To-delete --query 'SecurityGroups[*].{Name:GroupName,ID:GroupId}'
  
Output::

   [
     {
        "Name": "testfornewinstance", 
        "ID": "sg-33bb22aa"
     }, 
     {
        "Name": "newgrouptest", 
        "ID": "sg-1a2b3c4d"
     }
   ]

For more information, see `Using Security Groups`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Security Groups`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html

