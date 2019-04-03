**To list all executions for a Maintenance Window**

This example lists all of the executions for a Maintenance Window.

Command::

  aws ssm describe-maintenance-window-executions --window-id "mw-ab12cd34ef56gh78"

Output::

  {
    "WindowExecutions": [
        {
            "Status": "SUCCESS",
            "WindowId": "mw-06cf17cbefcb4bf4f",
            "StartTime": 1487692834.595,
            "EndTime": 1487692835.051,
            "WindowExecutionId": "518d5565-5969-4cca-8f0e-da3b2a638355"
        }
    ]
  }

**To list all executions for a Maintenance Window before a specified date**

This example lists all of the executions for a Maintenance Window before a specific date.

Command::

  aws ssm describe-maintenance-window-executions --window-id "mw-ab12cd34ef56gh78" --filters "Key=ExecutedBefore,Values=2016-11-04T05:00:00Z"
  
**To list all executions for a Maintenance Window after a specified date**

This example lists all of the executions for Maintenance Window after a specific date.

Command::

  aws ssm describe-maintenance-window-executions --window-id "mw-ab12cd34ef56gh78" --filters "Key=ExecutedAfter,Values=2016-11-04T17:00:00Z"