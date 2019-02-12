**To update a Maintenance Window**

This example updates the name of a Maintenance Window.

Command::

  aws ssm update-maintenance-window --window-id "mw-1a2b3c4d5e6f7g8h9" --name "My-Renamed-MW"

Output::

  {
	"Cutoff": 1,
	"Name": "My-Renamed-MW",
	"Schedule": "cron(0 16 ? * TUE *)",
	"Enabled": true,
	"AllowUnassociatedTargets": true,
	"WindowId": "mw-1a2b3c4d5e6f7g8h9",
	"Duration": 4
  }

**To enable a Maintenance Window**

This example enables a Maintenance Window.

Command::

  aws ssm update-maintenance-window --window-id "mw-1a2b3c4d5e6f7g8h9" --enabled
  
**To disable a Maintenance Window**
  
This example disables a Maintenance Window.

Command::

  aws ssm update-maintenance-window --window-id "mw-1a2b3c4d5e6f7g8h9" --no-enabled
  