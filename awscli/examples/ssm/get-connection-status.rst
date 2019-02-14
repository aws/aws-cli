**To determine whether connections can be made to an instance**

This example retrieves the Session Manager connection status for an instance to determine whether configured and able to receive Session Manager connections. 

Command::

  aws ssm get-connection-status --target "i-01d8e37ef8EXAMPLE"
  
Output::

  {
    "Target": "i-01d8e37ef8EXAMPLE",
    "Status": "connected"
  }
