**To end a Session Manager session**

This example permanently ends a session created by the user "Bob" and closes the data connection between the Session Manager client and SSM Agent on the instance.

Command::

  aws ssm terminate-session --session-id "Bob-0df8b88b07EXAMPLE"
  
Output::

  {
    "SessionId": "Bob-0df8b88b07EXAMPLE"
  } 
