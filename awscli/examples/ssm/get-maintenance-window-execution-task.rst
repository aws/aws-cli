**To get information about a Maintenance Window task execution**

This example lists information about a task that was part of a maintenance window execution.

Command::

  aws ssm get-maintenance-window-execution-task --window-execution-id "518d5565-5969-4cca-8f0e-da3b2a638355" --task-id "ac0c6ae1-daa3-4a89-832e-d384503b6586"

Output::

  {
    "Status": "SUCCESS",
    "MaxErrors": "1",
    "TaskArn": "AWS-RunShellScript",
    "MaxConcurrency": "1",
    "ServiceRole": "arn:aws:iam::812345678901:role/MaintenanceWindowsRole",
    "WindowExecutionId": "518d5565-5969-4cca-8f0e-da3b2a638355",
    "Priority": 10,
    "StartTime": 1487692834.684,
    "EndTime": 1487692835.005,
    "Type": "RUN_COMMAND",
    "TaskParameters": [
        {
            "commands": {
                "Values": [
                    "df"
                ]
            },
            "aws:InstanceId": {
                "Values": [
                    "i-0000293ffd8c57862"
                ]
            }
        }
    ],
    "TaskExecutionId": "ac0c6ae1-daa3-4a89-832e-d384503b6586"
  }
