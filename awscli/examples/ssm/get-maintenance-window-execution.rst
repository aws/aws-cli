**To get information about a Maintenance Window task execution**

This example lists information about a task executed as part of a maintenance window execution.

Command::

  aws ssm get-maintenance-window-execution --window-execution-id "518d5565-5969-4cca-8f0e-da3b2a638355"

Output::

  {
    "Status": "SUCCESS",
    "TaskIds": [
        "ac0c6ae1-daa3-4a89-832e-d384503b6586"
    ],
    "StartTime": 1487692834.595,
    "EndTime": 1487692835.051,
    "WindowExecutionId": "518d5565-5969-4cca-8f0e-da3b2a638355",
  }
