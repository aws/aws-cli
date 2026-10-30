**Example 1: To list all executions for a maintenance window**

The following ``describe-maintenance-window-executions`` example lists all of the executions for the specified maintenance window. ::

    aws ssm describe-maintenance-window-executions \
        --window-id "mw-ab12cd34eEXAMPLE"

Output::

    {
        "WindowExecutions": [
            {
                "WindowId": "mw-ab12cd34eEXAMPLE",
                "WindowExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Status": "IN_PROGRESS",
                "StartTime": "2021-08-04T11:00:00.000000-07:00"

            },
            {
                "WindowId": "mw-ab12cd34eEXAMPLE",
                "WindowExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Status": "SUCCESS",
                "StartTime": "2021-08-03T11:00:00.000000-07:00",
                "EndTime": "2021-08-03T11:37:21.450000-07:00"
            },
            {
                "WindowId": "mw-ab12cd34eEXAMPLE",
                "WindowExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Status": "FAILED",
                "StatusDetails": "One or more tasks in the orchestration failed.",
                "StartTime": "2021-08-02T11:00:00.000000-07:00",
                "EndTime": "2021-08-02T11:22:36.190000-07:00"
            }
        ]
    }

**Example 2: To list all executions for a maintenance window before a specified date**

The following ``describe-maintenance-window-executions`` example lists all of the executions for the specified maintenance window before the specified date. ::

    aws ssm describe-maintenance-window-executions \
        --window-id "mw-ab12cd34eEXAMPLE" \
        --filters "Key=ExecutedBefore,Values=2021-08-03T00:00:00Z"

Output::

    {
        "WindowExecutions": [
            {
                "WindowId": "mw-ab12cd34eEXAMPLE",
                "WindowExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Status": "FAILED",
                "StatusDetails": "One or more tasks in the orchestration failed.",
                "StartTime": "2021-08-02T11:00:00.000000-07:00",
                "EndTime": "2021-08-02T11:22:36.190000-07:00"
            }
        ]
    }

**Example 3: To list all executions for a maintenance window after a specified date**

The following ``describe-maintenance-window-executions`` example lists all of the executions for the specified maintenance window after the specified date. ::

    aws ssm describe-maintenance-window-executions \
        --window-id "mw-ab12cd34eEXAMPLE" \
        --filters "Key=ExecutedAfter,Values=2021-08-04T00:00:00Z"

Output::

    {
        "WindowExecutions": [
            {
                "WindowId": "mw-ab12cd34eEXAMPLE",
                "WindowExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Status": "IN_PROGRESS",
                "StartTime": "2021-08-04T11:00:00.000000-07:00"
            }
        ]
    }

For more information, see `View information about tasks and task executions (AWS CLI)  <https://docs.aws.amazon.com/systems-manager/latest/userguide/mw-cli-tutorial-task-info.html>`__ in the *AWS Systems Manager User Guide*.