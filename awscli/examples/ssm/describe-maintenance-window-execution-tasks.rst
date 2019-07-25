**To list all tasks associated with a Maintenance Window Execution**

This example lists the tasks associated with a Maintenance Window execution.

Command::

  aws ssm describe-maintenance-window-execution-tasks --window-execution-id "518d5565-5969-4cca-8f0e-da3b2a638355"

Output::

  {
    "WindowExecutionTaskIdentities": [
        {
            "Status": "SUCCESS",
            "TaskArn": "AWS-RunShellScript",
            "StartTime": 1487692834.684,
            "TaskType": "RUN_COMMAND",
            "EndTime": 1487692835.005,
            "WindowExecutionId": "518d5565-5969-4cca-8f0e-da3b2a638355",
            "TaskExecutionId": "ac0c6ae1-daa3-4a89-832e-d384503b6586"
        }
    ]
  }
