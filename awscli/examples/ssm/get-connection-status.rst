**To display the connection status of a managed instance**

This example returns the connection status of the managed instance ``i-1234567890abcdef0``.

Command::

  aws ssm get-connection-status --target i-1234567890abcdef0

Output::

  {
    "Target": "i-1234567890abcdef0",
    "Status": "connected"
  }
