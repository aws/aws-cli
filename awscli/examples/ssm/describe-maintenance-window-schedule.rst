**To list upcoming executions for a Maintenance Window**

This example lists upcoming executions for a Maintenance Window.

Command::

  aws ssm describe-maintenance-window-schedule --window-id mw-ab12cd34ef56gh78

Output::

  {
    "ScheduledWindowExecutions": [
        {
            "WindowId": "mw-ab12cd34ef56gh78",
            "Name": "My-First-Maintenance-Window",
            "ExecutionTime": "2019-02-19T16:00Z"
        },
		{
            "WindowId": "mw-ab12cd34ef56gh78",
            "Name": "My-First-Maintenance-Window",
            "ExecutionTime": "2019-02-26T16:00Z"
        },
		...
    ]
  }