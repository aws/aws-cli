**To get information about a Maintenance Window**

This example gets details about a Maintenance Window.

Command::

  aws ssm get-maintenance-window --window-id "mw-03eb9db42890fb82d"

Output::

  {
    "Cutoff": 1,
    "Name": "TestMaintWin",
    "Schedule": "cron(0 */30 * * * ? *)",
    "Enabled": true,
    "AllowUnassociatedTargets": false,
    "WindowId": "mw-03eb9db42890fb82d",
    "ModifiedDate": 1487614445.527,
    "CreatedDate": 1487614445.527,
    "Duration": 2
  }
