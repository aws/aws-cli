**To start a Session Manager session**

This example makes a connection with an instance for a Session Manager session.

Note that this interactive command requires the Session Manager plugin to be installed on the client machine making the call. For more information, see `<link-text>` in the *AWS Systems Manager User Guide*.

.. _`<Install the Session Manager Plugin for the AWS CLI>`: http://docs.aws.amazon.com/<product>/latest/<guide>/<page>.html

Command::

  aws ssm start-session --target "i-01d8e37ef8EXAMPLE"
  
Output::

  Starting session with SessionId: Bob-0df8b88b07EXAMPLE
