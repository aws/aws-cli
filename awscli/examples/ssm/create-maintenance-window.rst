**To create a maintenance window**

This example creates a new maintenance window with the specified name that runs at 4 PM on every Tuesday for 4 hours, with a 1 hour cutoff, and that allows unassociated targets.

Command::

  aws ssm create-maintenance-window --name "My-First-Maintenance-Window" --schedule "cron(0 16 ? * TUE *)" --duration 4 --cutoff 1 --allow-unassociated-targets

Output::

  {
	"WindowId": "mw-ab12cd34ef56gh78"
  }
