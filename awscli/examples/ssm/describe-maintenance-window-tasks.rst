**Example 1: To list all tasks for a maintenance window**

The following ``describe-maintenance-window-tasks`` example lists all of the tasks for the specified maintenance window. ::

    aws ssm describe-maintenance-window-tasks \
        --window-id "mw-06cf17cbefEXAMPLE"

Output::

    {
        "Tasks": [
            {
                "ServiceRoleArn": "arn:aws:iam::<aws_account_id>:role/MaintenanceWindowsRole",
                "MaxErrors": "1",
                "TaskArn": "AWS-RunShellScript",
                "MaxConcurrency": "1",
                "WindowTaskId": "a23e338d-ff30-4398-8aa3-09cd0EXAMPLE",
                "TaskParameters": {
                    "commands": {
                        "Values": [
                            "df"
                        ]
                    }
                },
                "Priority": 10,
                "WindowId": "mw-06cf17cbefEXAMPLE",
                "Type": "RUN_COMMAND",
                "Targets": [
                    {
                        "Values": [
                            "i-0000293ffdmw-06cf17cbefEXAMPLE"
                        ],
                        "Key": "InstanceIds"
                    }
                ]
            }
        ]
    }

**Example 2: To list all tasks for a maintenance window that invokes the AWS-RunPowerShellScript command document**

The following ``describe-maintenance-window-tasks`` example lists all of the tasks for the specified maintenance window that invokes the ``AWS-RunPowerShellScript`` command document. ::

    aws ssm describe-maintenance-window-tasks \
        --window-id "mw-ab12cd34eEXAMPLE" \
        --filters "Key=TaskArn,Values=AWS-RunPowerShellScript"

Output::

    {
        "Tasks": [
            {
                "WindowId": "mw-ab12cd34eEXAMPLE",
                "WindowTaskId": "0d36e6b4-3a4f-411e-adcb-3558eEXAMPLE",
                "TaskArn": "AWS-RunPowerShellScript",
                "Type": "RUN_COMMAND",
                "Targets": [
                    {
                        "Key": "WindowTargetIds",
                        "Values": [
                            "da89dcc3-7f9c-481d-ba2b-edcb7EXAMPLE"
                        ]
                    }
                ],
                "TaskParameters": {},
                "Priority": 1,
                "ServiceRoleArn": "arn:aws:iam::111222333444:role/aws-service-role/ssm.amazonaws.com/AWSServiceRoleForAmazonSSM",
                "MaxConcurrency": "1",
                "MaxErrors": "1",
                "Name": "MyTask"
            }
        ]
    }

**Example 3: To list all tasks for a maintenance window that have a Priority of 3**

The following ``describe-maintenance-window-tasks`` example lists all of the tasks for the specified maintenance window that have a ``Priority`` of ``3``. ::

    aws ssm describe-maintenance-window-tasks \
        --window-id "mw-ab12cd34eEXAMPLE" \
        --filters "Key=Priority,Values=3"    

Output::

    {
        "Tasks": [
            {
                "WindowId": "mw-ab12cd34eEXAMPLE",
                "WindowTaskId": "0d36e6b4-3a4f-411e-adcb-3558eEXAMPLE",
                "TaskArn": "AWS-RunPowerShellScript",
                "Type": "RUN_COMMAND",
                "Targets": [
                    {
                        "Key": "WindowTargetIds",
                        "Values": [
                            "da89dcc3-7f9c-481d-ba2b-edcb7EXAMPLE"
                        ]
                    }
                ],
                "TaskParameters": {},
                "Priority": 3,
                "ServiceRoleArn": "arn:aws:iam::111222333444:role/aws-service-role/ssm.amazonaws.com/AWSServiceRoleForAmazonSSM",
                "MaxConcurrency": "1",
                "MaxErrors": "1",
                "Name": "MyRunCommandTask"
            },
            {
                "WindowId": "mw-ab12cd34eEXAMPLE",
                "WindowTaskId": "ee45feff-ad65-4a6c-b478-5cab8EXAMPLE",
                "TaskArn": "AWS-RestartEC2Instance",
                "Type": "AUTOMATION",
                "Targets": [
                    {
                        "Key": "WindowTargetIds",
                        "Values": [
                            "da89dcc3-7f9c-481d-ba2b-edcb7EXAMPLE"
                        ]
                    }
                ],
                "TaskParameters": {},
                "Priority": 3,
                "ServiceRoleArn": "arn:aws:iam::111222333444:role/aws-service-role/ssm.amazonaws.com/AWSServiceRoleForAmazonSSM",
                "MaxConcurrency": "10",
                "MaxErrors": "5",
                "Name": "My-Automation-Task",
                "Description": "A description for my Automation task"
            }
        ]
    }

**To list all tasks for a maintenance window that have a Priority of 1 and use Run Command**

This ``describe-maintenance-window-tasks`` example lists all of the tasks for the specified maintenance window that have a ``Priority`` of ``1`` and use ``Run Command``. ::

    aws ssm describe-maintenance-window-tasks \
        --window-id "mw-ab12cd34eEXAMPLE" \
        --filters "Key=Priority,Values=1" "Key=TaskType,Values=RUN_COMMAND"
        
Output::

    {
        "Tasks": [
            {
                "WindowId": "mw-ab12cd34eEXAMPLE",
                "WindowTaskId": "0d36e6b4-3a4f-411e-adcb-3558eEXAMPLE",
                "TaskArn": "AWS-RunPowerShellScript",
                "Type": "RUN_COMMAND",
                "Targets": [
                    {
                        "Key": "WindowTargetIds",
                        "Values": [
                            "da89dcc3-7f9c-481d-ba2b-edcb7EXAMPLE"
                        ]
                    }
                ],
                "TaskParameters": {},
                "Priority": 1,
                "ServiceRoleArn": "arn:aws:iam::111222333444:role/aws-service-role/ssm.amazonaws.com/AWSServiceRoleForAmazonSSM",
                "MaxConcurrency": "1",
                "MaxErrors": "1",
                "Name": "MyRunCommandTask"
            }
        ]
    }

For more information, see `View Information About Maintenance Windows (AWS CLI) <https://docs.aws.amazon.com/systems-manager/latest/userguide/maintenance-windows-cli-tutorials-describe.html>`__ in the *AWS Systems Manager User Guide*.
