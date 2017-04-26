**To list all tasks for a Maintenance Window**

This example lists all of the tasks for a maintenance window.

Command::

  aws ssm describe-maintenance-window-tasks --window-id "mw-06cf17cbefcb4bf4f"

Output::

  {
    "Tasks": [
        {
            "ServiceRoleArn": "arn:aws:iam::<aws_account_id>:role/MaintenanceWindowsRole",
            "MaxErrors": "1",
            "TaskArn": "AWS-RunShellScript",
            "MaxConcurrency": "1",
            "WindowTaskId": "a23e338d-ff30-4398-8aa3-09cd052ebf17",
            "TaskParameters": {
                "commands": {
                    "Values": [
                        "df"
                    ]
                }
            },
            "Priority": 10,
            "WindowId": "mw-06cf17cbefcb4bf4f",
            "Type": "RUN_COMMAND",
            "Targets": [
                {
                    "Values": [
                        "i-0000293ffd8c57862"
                    ],
                    "Key": "InstanceIds"
                }
            ]
        }
    ]
  }

**To list all tasks for a maintenance window that invoke the AWS-RunPowerShellScript Run Command**

This example lists all of the tasks for a maintenance window that invoke the ``AWS-RunPowerShellScript`` Run Command.

Command::

  aws ssm describe-maintenance-window-tasks --window-id "mw-ab12cd34ef56gh78" --filters "Key=TaskArn,Values=AWS-RunPowerShellScript"

**To list all tasks for a maintenance window that have a Priority of 3**

This example lists all of the tasks for a maintenance window that have a ``Priority`` of ``3``.

Command::

  aws ssm describe-maintenance-window-tasks --window-id "mw-ab12cd34ef56gh78" --filters "Key=Priority,Values=3"
  
**To list all tasks for a maintenance window that have a Priority of 1 and use Run Command**

This example lists all of the tasks for a maintenance window that have a ``Priority`` of ``1`` and use ``Run Command``.

Command::

  aws ssm describe-maintenance-window-tasks --window-id "mw-ab12cd34ef56gh78" --filters "Key=Priority,Values=1" "Key=TaskType,Values=RUN_COMMAND"