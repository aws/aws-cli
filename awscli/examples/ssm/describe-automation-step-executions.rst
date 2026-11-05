**Example 1: To describe all steps for an automation execution**

The following ``describe-automation-step-executions`` example displays details about the steps of an Automation execution. ::

    aws ssm describe-automation-step-executions \
        --automation-execution-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "StepExecutions": [
            {
                "StepName": "startInstances",
                "Action": "aws:changeInstanceState",
                "ExecutionStartTime": 1583737234.134,
                "ExecutionEndTime": 1583737234.672,
                "StepStatus": "Success",
                "Inputs": {
                    "DesiredState": "\"running\"",
                    "InstanceIds": "[\"i-0cb99161f6EXAMPLE\"]"
                },
                "Outputs": {
                    "InstanceStates": [
                        "running"
                    ]
                },
                "StepExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "OverriddenParameters": {}
            }
        ]
    }

**Example 2: To describe a specific step for an automation execution**

The following ``describe-automation-step-executions`` example displays details about a specific step of an Automation execution. ::

    aws ssm describe-automation-step-executions \
        --automation-execution-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --filters Key=StepExecutionId,Values=a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "StepExecutions": [
            {
                "StepName": "startInstances",
                "Action": "aws:changeInstanceState",
                "ExecutionStartTime": 1583737234.134,
                "ExecutionEndTime": 1583737234.672,
                "StepStatus": "Success",
                "Inputs": {
                    "DesiredState": "\"running\"",
                    "InstanceIds": "[\"i-0cb99161f6EXAMPLE\"]"
                },
                "Outputs": {
                    "InstanceStates": [
                        "running"
                    ]
                },
                "StepExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "OverriddenParameters": {}
            }
        ]
    }

For more information, see `Running an Automation Workflow Step by Step (Command Line) <https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-working-executing-manually.html#automation-working-executing-manually-commandline>`__ in the *AWS Systems Manager User Guide*.
