**To get information about a maintenance window task execution**

The following ``get-maintenance-window-execution-task`` example lists information about a task that is part of the specified maintenance window execution. ::

    aws ssm get-maintenance-window-execution-task \
        --window-execution-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --task-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"

Output::

    {
        "WindowExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "TaskExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "TaskArn": "AWS-RunPatchBaseline",
        "ServiceRole": "arn:aws:iam::123456789012:role/aws-service-role/ssm.amazonaws.com/AWSServiceRoleForAmazonSSM",
        "Type": "RUN_COMMAND",
        "TaskParameters": [
            {
                "BaselineOverride": {
                    "Values": [
                        ""
                    ]
                },
                "InstallOverrideList": {
                    "Values": [
                        ""
                    ]
                },
                "Operation": {
                    "Values": [
                        "Scan"
                    ]
                },
                "RebootOption": {
                    "Values": [
                        "RebootIfNeeded"
                    ]
                },
                "SnapshotId": {
                    "Values": [
                        "{{ aws:ORCHESTRATION_ID }}"
                    ]
                },
                "aws:InstanceId": {
                    "Values": [
                        "i-02573cafcfEXAMPLE",
                        "i-0471e04240EXAMPLE",
                        "i-07782c72faEXAMPLE"
                    ]
                }
            }
        ],
        "Priority": 1,
        "MaxConcurrency": "1",
        "MaxErrors": "3",
        "Status": "SUCCESS",
        "StartTime": "2021-08-04T11:45:35.088000-07:00",
        "EndTime": "2021-08-04T11:53:09.079000-07:00"
    }

For more information, see `View information about tasks and task executions (AWS CLI) <https://docs.aws.amazon.com/systems-manager/latest/userguide/mw-cli-tutorial-task-info.html>`__ in the *AWS Systems Manager User Guide*.