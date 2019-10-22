**To list all Maintenance Windows**

This example lists all Maintenance Windows on your account.

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

**To list all enabled Maintenance Windows**
  
This example lists all enabled Maintenance Windows.

Command::

  aws ssm describe-maintenance-windows --filters "Key=Enabled,Values=true"
  
**To list Maintenance Windows matching a specific name**
  
This example lists all Maintenance Windows with a specific name value.

Command::

  aws ssm describe-maintenance-windows --filters "Key=Name,Values=MyMaintenanceWindow"
  