**To get information about a maintenance window task execution**

The following ``get-maintenance-window-execution-task`` example lists information about a task that is part of the specified maintenance window execution. ::

    aws ssm get-maintenance-window-execution-task \
        --window-execution-id "518d5565-5969-4cca-8f0e-da3b2EXAMPLE" \
        --task-id "ac0c6ae1-daa3-4a89-832e-d3845EXAMPLE"

Output::

    {
        "Status": "SUCCESS",
        "MaxErrors": "1",
        "TaskArn": "AWS-RunShellScript",
        "MaxConcurrency": "1",
        "ServiceRole": "arn:aws:iam::111222333444:role/MaintenanceWindowsRole",
        "WindowExecutionId": "518d5565-5969-4cca-8f0e-da3b2EXAMPLE",
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
                        "i-0000293ffdEXAMPLE"
                    ]
                }
            }
        ],
        "TaskExecutionId": "ac0c6ae1-daa3-4a89-832e-d3845EXAMPLE"
    }

For more information, see `View Information About Tasks and Task Executions (AWS CLI) <https://docs.aws.amazon.com/systems-manager/latest/userguide/mw-cli-tutorial-task-info.html>`__ in the *AWS Systems Manager User Guide*.
