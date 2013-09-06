**To delete a key pair**

This example deletes the key pair named ``MyKeyPair``.

Command::

  aws ec2 delete-key-pair --key-name MyKeyPair

Output::

  {
      "return": "true"
  }

For more information, see `Using Key Pairs`_ in the *AWS Command Line Interface User Guide*.

.. _`Using Key Pairs`: http://docs.aws.amazon.com/cli/latest/userguide/cli-ec2-keypairs.html

