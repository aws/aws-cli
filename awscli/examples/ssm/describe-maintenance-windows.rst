**To list all maintenance windows**

This example lists all maintenance windows on your account.

Command::

  aws ssm describe-maintenance-windows

Output::

  {
    "WindowIdentities": [
        {
            "Duration": 2,
            "Cutoff": 1,
            "WindowId": "mw-03eb9db42890fb82d",
            "Enabled": true,
            "Name": "TestMaintWin"
        },
    ]
  }

**To list all maintenance windows in a region**

This example lists all maintenance windows in the ``us-west-1`` region.

Command::

  aws ssm describe-maintenance-windows --region "us-west-1"
  
**To list all enabled maintenance windows**
  
This example lists all enabled maintenance windows.

Command::

  aws ssm describe-maintenance-windows --filters "Key=Enabled,Values=true"