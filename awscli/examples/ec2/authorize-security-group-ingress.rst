**[EC2-Classic] To add a rule to a security group that allows inbound SSH traffic**

This example enables inbound traffic on TCP port 22 (SSH).

Command::

  aws ec2 authorize-security-group-ingress --group-name MySecurityGroup --protocol tcp --port 22 --cidr 203.0.113.0/24

Output::

  {
      "return": "true"
  }

**[EC2-VPC] To add a rule to a security group that allows inbound SSH traffic**

This example enables inbound traffic on TCP port 22 (SSH). Note that you can't reference a security group for EC2-VPC by name.

Command::

  aws ec2 authorize-security-group-ingress --group-id sg-903004f8 --protocol tcp --port 22 --cidr 203.0.113.0/24

Output::

  {
      "return": "true"
  }

For more information, see `Using Security Groups`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Security Groups`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html

