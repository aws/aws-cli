**To start a Session Manager session**

This example establishes a connection with an instance for a Session Manager session.

Note that this interactive command requires the Session Manager plugin to be installed on the client machine making the call. For more information, see `Install the Session Manager Plugin for the AWS CLI`_ in the *AWS Systems Manager User Guide*.

.. _`Install the Session Manager Plugin for the AWS CLI`: http://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html

Command::

  aws ssm start-session --target "i-1234567890abcdef0"
  
Output::

  Starting session with SessionId: Erik-07a16060613c408b5

