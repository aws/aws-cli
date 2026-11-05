**To list all tasks associated with a maintenance window execution**

The following ``describe-maintenance-window-execution-tasks`` example lists the tasks associated with the specified maintenance window execution. ::

    aws ssm describe-maintenance-window-execution-tasks \
        --window-execution-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "WindowExecutionTaskIdentities": [
            {
                "Status": "SUCCESS",
                "TaskArn": "AWS-RunShellScript",
                "StartTime": 1487692834.684,
                "TaskType": "RUN_COMMAND",
                "EndTime": 1487692835.005,
                "WindowExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "TaskExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }
        ]
    }

For more information, see `View Information About Tasks and Task Executions (AWS CLI) <https://docs.aws.amazon.com/systems-manager/latest/userguide/mw-cli-tutorial-task-info.html>`__ in the *AWS Systems Manager User Guide*.
