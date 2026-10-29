**To get information about a maintenance window task invocation**

The following ``get-maintenance-window-execution-task-invocation`` example lists information about the specified task invocation that is part of the specified maintenance window execution. ::

    aws ssm get-maintenance-window-execution-task-invocation \
        --window-execution-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111" \
        --task-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222" \
        --invocation-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333"

Output::

    {
        "Status": "SUCCESS",
        "Parameters": "{\"comment\":\"\",\"documentName\":\"AWS-RunPowerShellScript\",\"instanceIds\":[\"i-1234567890EXAMPLE\"],\"maxConcurrency\":\"1\",\"maxErrors\":\"1\",\"parameters\":{\"executionTimeout\":[\"3600\"],\"workingDirectory\":[\"\"],\"commands\":[\"echo Hello\"]},\"timeoutSeconds\":600}",
        "ExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
        "InvocationId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
        "StartTime": 1549998326.421,
        "TaskType": "RUN_COMMAND",
        "EndTime": 1550001931.784,
        "WindowExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "StatusDetails": "Failed",
        "TaskExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
    }

For more information, see `View Information About Tasks and Task Executions (AWS CLI) <https://docs.aws.amazon.com/systems-manager/latest/userguide/mw-cli-tutorial-task-info.html>`__ in the *AWS Systems Manager User Guide*.
