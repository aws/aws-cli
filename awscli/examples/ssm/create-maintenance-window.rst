**To create a Maintenance Window**

This example creates a new Maintenance Window with the specified name that runs at 4 PM UTC on every Tuesday for 4 hours, with a 1 hour cutoff, and that allows unassociated targets.

Command::

  aws ssm create-maintenance-window --name "My-First-Maintenance-Window" --schedule "cron(0 16 ? * TUE *)" --duration 4 --cutoff 1 --allow-unassociated-targets

Output::

  {
	"WindowId": "mw-ab12cd34ef56gh78"
  }

**To create a Maintenance Window with a specific start and end date**

This example creates a new Maintenance Window with the specified name that runs at 4 PM UTC on every Tuesday for 4 hours, with a 1 hour cutoff, and that allows unassociated targets.  The Maintenance Window created will not become active until the specified start date and becomes inactive at the specified end date.

Command::

  aws ssm create-maintenance-window --name "My-First-Maintenance-Window" --start-date 2019-03-13T19:00:00Z --end-date 2019-03-23T19:00:00Z --duration 4 --cutoff 1 --allow-unassociated-targets --schedule "cron(0 16 ? * TUE *)"

Output::

  {
	"WindowId": "mw-ab12cd34ef56gh78"
  }
