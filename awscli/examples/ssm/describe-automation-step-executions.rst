**To get details about all active and terminated step executions in an Automation workflow**

This example displays the details of all step executions of an Automation workflow.

Command::

  aws ssm describe-automation-step-executions --automation-execution-id 4105a4fc-f944-11e6-9d32-0a1b2c3d495h

Output::

  {
    "StepExecutions": [
        {
            "StepName": "startInstances",
            "Action": "aws:changeInstanceState",
            "ExecutionStartTime": 1550083651.597,
            "ExecutionEndTime": 1550083872.358,
            "StepStatus": "Success",
            "Inputs": {
                "DesiredState": "\"running\"",
                "InstanceIds": "[\"i-1234567890abcdef0\"]"
            },
            "Outputs": {
                "InstanceStates": [
                    "running"
                ]
            },
            "StepExecutionId": "bd010896-b1d5-4028-b869-0a1b2c3d4f95",
            "OverriddenParameters": {}
        }
    ]
  }

**To get details about a specific step execution in an Automation workflow**

This example returns the details for a specific step within an Automation workflow.

Command::

  aws ssm describe-automation-step-executions --automation-execution-id 4105a4fc-f944-11e6-9d32-0a1b2c3d495h --filters "Key=StepExecutionId,Values=bd010896-b1d5-4028-b869-0a1b2c3d4f95"
