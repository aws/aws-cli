**To remove a task from a maintenance window**

This example removes task ``1a2b3c4d-1a2b-1a2b-1a2b-1a2b3c4d5e6c`` from Maintenance Window ``mw-ab12cd34ef56gh78``.

Command::

  aws ssm deregister-task-from-maintenance-window --window-id "mw-ab12cd34ef56gh78" --window-task-id "1a2b3c4d-1a2b-1a2b-1a2b-1a2b3c4d5e6c"
  
Output::

  {
	"WindowTaskId":"1a2b3c4d-1a2b-1a2b-1a2b-1a2b3c4d5e6c",
	"WindowId":"mw-ab12cd34ef56gh78"
  }
