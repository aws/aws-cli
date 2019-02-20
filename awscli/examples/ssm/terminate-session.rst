**To end a Session Manager session**

This example permanently ends a session that was created by the user "Bob" and closes the data connection between the Session Manager client and SSM Agent on the instance.

Command::

  aws ssm terminate-session --session-id "Bob-07a16060613c408b5"

Output::

  {
    "SessionId": "Bob-07a16060613c408b5"
  }
