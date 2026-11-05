**To get information about a maintenance window task execution**

The following ``get-maintenance-window-execution`` example lists information about a task executed as part of the specified maintenance window execution. ::

    aws ssm get-maintenance-window-execution \
        --window-execution-id "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"

Output::

    {
        "Status": "SUCCESS",
        "TaskIds": [
            "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
        ],
        "StartTime": 1487692834.595,
        "EndTime": 1487692835.051,
        "WindowExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `View Information About Tasks and Task Executions (AWS CLI) <https://docs.aws.amazon.com/systems-manager/latest/userguide/mw-cli-tutorial-task-info.html>`__ in the *AWS Systems Manager User Guide*.
