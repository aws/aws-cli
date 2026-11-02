**To get the specific task invocations performed for a maintenance window task execution**

The following ``describe-maintenance-window-execution-task-invocations`` example lists the invocations for the specified task executed as part of the specified maintenance window execution. ::

    aws ssm describe-maintenance-window-execution-task-invocations \
        --window-execution-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --task-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"

Output::

    {
        "WindowExecutionTaskInvocationIdentities": [
            {
                "Status": "SUCCESS",
                "Parameters": "{\"documentName\":\"AWS-RunShellScript\",\"instanceIds\":[\"i-0000293ffd8c57862\"],\"parameters\":{\"commands\":[\"df\"]},\"maxConcurrency\":\"1\",\"maxErrors\":\"1\"}",
                "InvocationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "StartTime": 1487692834.723,
                "EndTime": 1487692834.871,
                "WindowExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "TaskExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }
        ]
    }

For more information, see `View Information About Tasks and Task Executions (AWS CLI) <https://docs.aws.amazon.com/systems-manager/latest/userguide/mw-cli-tutorial-task-info.html>`__ in the *AWS Systems Manager User Guide*.
