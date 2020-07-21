**Example 1: To list all executions for a maintenance window**

The following ``describe-maintenance-window-executions`` example lists all of the executions for the specified maintenance window. ::

    aws ssm describe-maintenance-window-executions \
        --window-id "mw-ab12cd34eEXAMPLE"

Output::

    {
        "WindowExecutions": [
            {
                "Status": "SUCCESS",
                "WindowId": "mw-ab12cd34eEXAMPLE",
                "StartTime": 1487692834.595,
                "EndTime": 1487692835.051,
                "WindowExecutionId": "518d5565-5969-4cca-8f0e-da3b2a638355"
            }
        ]
    }

**Example 2: To list all executions for a maintenance window before a specified date**

The following ``describe-maintenance-window-executions`` example lists all of the executions for the specified maintenance window before the specified date. ::

    aws ssm describe-maintenance-window-executions \
        --window-id "mw-ab12cd34eEXAMPLE" \
        --filters "Key=ExecutedBefore,Values=2020-11-04T05:00:00Z"

Output::

    {
        "WindowExecutions": [
            {
                "WindowId": "mw-ab12cd34eEXAMPLE",
                "WindowExecutionId": "407a2cc0-9602-4463-af87-9d94bEXAMPLE",
                "Status": "SUCCESS",
                "StartTime": 1581546172.042,
                "EndTime": 1581546172.454
            },
            {
                "WindowId": "mw-ab12cd34eEXAMPLE",
                "WindowExecutionId": "a45d2571-f225-45a2-b448-bf57aEXAMPLE",
                "Status": "FAILED",
                "StatusDetails": "One or more tasks in the orchestration failed.",
                "StartTime": 1579891950.312,
                "EndTime": 1579891950.35
            }
        ]
    }
        
**Example 3: To list all executions for a maintenance window after a specified date**

The following ``describe-maintenance-window-executions`` example lists all of the executions for the specified maintenance window after the specified date. ::

    aws ssm describe-maintenance-window-executions \
        --window-id "mw-ab12cd34eEXAMPLE" \
        --filters "Key=ExecutedAfter,Values=2016-11-04T17:00:00Z"

Output::

    {
        "WindowExecutions": [
            {
                "WindowId": "mw-ab12cd34eEXAMPLE",
                "WindowExecutionId": "f4ad7a92-d83f-4569-a437-dea8fe74e315EXAMPLE",
                "Status": "SUCCESS",
                "StartTime": 1581546531.776,
                "EndTime": 1581546532.219
            },
            {
                "WindowId": "mw-ab12cd34eEXAMPLE",
                "WindowExecutionId": "0bb99ef3-c3cc-4160-bded-d3e61EXAMPLE",
                "Status": "SUCCESS",
                "StartTime": 1581546352.01,
                "EndTime": 1581546352.403
            },
            {
                "WindowId": "mw-ab12cd34eEXAMPLE",
                "WindowExecutionId": "407a2cc0-9602-4463-af87-9d94bEXAMPLE",
                "Status": "SUCCESS",
                "StartTime": 1581546172.042,
                "EndTime": 1581546172.454
            }
        ]
    }

For more information, see `View Information About Tasks and Task Executions (AWS CLI) <https://docs.aws.amazon.com/systems-manager/latest/userguide/mw-cli-tutorial-task-info.html>`__ in the *AWS Systems Manager User Guide*.
