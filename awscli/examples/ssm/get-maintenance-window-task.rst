**To get information about a maintenance window task**

The following ``get-maintenance-window-task`` example retrieves details about the specified maintenance window task. ::

    aws ssm get-maintenance-window-task \
        --window-id mw-0c5ed765acEXAMPLE \
        --window-task-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "ServiceRoleArn": "arn:aws:iam::123456789012:role/aws-service-role/ssm.amazonaws.com/AWSServiceRoleForAmazonSSM",
        "MaxErrors": "1",
        "TaskArn": "AWS-RunPowerShellScript",
        "MaxConcurrency": "1",
        "WindowTaskId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "TaskParameters": {},
        "Priority": 1,
        "TaskInvocationParameters": {
            "RunCommand": {
                "Comment": "",
                "TimeoutSeconds": 600,
                "Parameters": {
                    "commands": [
                        "echo Hello"
                    ],
                    "executionTimeout": [
                        "3600"
                    ],
                    "workingDirectory": [
                        ""
                    ]
                }
            }
        },
        "WindowId": "mw-0c5ed765acEXAMPLE",
        "TaskType": "RUN_COMMAND",
        "Targets": [
            {
                "Values": [
                    "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
                ],
                "Key": "WindowTargetIds"
            }
        ],
        "Name": "ExampleTask"
    }

For more information, see `View Information About Maintenance Windows (AWS CLI)  <https://docs.aws.amazon.com/systems-manager/latest/userguide/maintenance-windows-cli-tutorials-describe.html>`__ in the *AWS Systems Manager User Guide*.
