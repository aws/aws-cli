**To delete a security group**

This example deletes the security group named ``MySecurityGroup``.

Command::

  aws ec2 delete-security-group --group-name MySecurityGroup

Output::

  {
      "return": "true"
  }

For more information, see `Using Security Groups`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Security Groups`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-sg.html
