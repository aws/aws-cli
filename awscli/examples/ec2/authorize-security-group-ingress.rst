**To add a rule to a security group that allow inbound SSH traffic**

This example enables inbound traffic on TCP port 22 (SSH).

Command::

  aws ec2 authorize-security-group-ingress --group-name MySecurityGroup --protocol tcp --port 22 --cidr 203.0.113.0/24

Output::

  {
      "return": "true"
  }


For more information, see `Using Security Groups`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Security Groups`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html

