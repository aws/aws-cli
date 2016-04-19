**To get the console output**

This example gets the console ouput for the specified Linux instance.

Command::

  aws ec2 get-console-output --instance-id i-1234567890abcdef0

Output::

  {
      "InstanceId": "i-1234567890abcdef0",
      "Timestamp": "2013-07-25T21:23:53.000Z",
      "Output": "..."
  }

