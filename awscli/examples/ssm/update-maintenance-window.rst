**To update a maintenance window**

This example updates the name of a maintenance window.

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

**To enable a maintenance window**

This example enables a maintenance window.

Command::

  aws ssm update-maintenance-window --window-id "mw-1a2b3c4d5e6f7g8h9" --enabled
  
**To disable a maintenance window**
  
This example disables a maintenance window.

Command::

  aws ssm update-maintenance-window --window-id "mw-1a2b3c4d5e6f7g8h9" --no-enabled
  