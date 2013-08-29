**To create a security group**

This example creates a security group named MySecurityGroup.

Command::

  aws ec2 create-security-group --group-name MySecurityGroup --description "My security group"

Output::

  {
      "return": "true"
      "GroupId": "sg-903004f8"
  }

For more information, see `Using Security Groups`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Security Groups`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html
