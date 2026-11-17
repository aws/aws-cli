**To display details about an automation execution**

The following ``get-automation-execution`` example displays detailed information about an Automation execution. ::

    aws ssm get-automation-execution \
        --automation-execution-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "AutomationExecution": {
            "AutomationExecutionId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "DocumentName": "AWS-StartEC2Instance",
            "DocumentVersion": "1",
            "ExecutionStartTime": 1583737233.748,
            "ExecutionEndTime": 1583737234.719,
            "AutomationExecutionStatus": "Success",
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
            ],
            "StepExecutionsTruncated": false,
            "Parameters": {
                "AutomationAssumeRole": [
                    ""
                ],
                "InstanceId": [
                    "i-0cb99161f6EXAMPLE"
                ]
            },
            "Outputs": {},
            "Mode": "Auto",
            "ExecutedBy": "arn:aws:sts::29884EXAMPLE:assumed-role/mw_service_role/OrchestrationService",
            "Targets": [],
            "ResolvedTargets": {
                "ParameterValues": [],
                "Truncated": false
            }
        }
    }

For more information, see `Walkthrough: Patch a Linux AMI (AWS CLI) <https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-walk-patch-linux-ami-cli.html>`__ in the *AWS Systems Manager User Guide*.
