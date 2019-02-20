**To determine whether connections can be made to an instance**

This example retrieves the Session Manager connection status for an instance to determine whether it is configured and able to receive Session Manager connections.

Command::

  aws ssm get-connection-status --target "i-1234567890abcdef0"

Output::

  {
    "Target": "i-1234567890abcdef0",
	"Status": "connected"
  }
