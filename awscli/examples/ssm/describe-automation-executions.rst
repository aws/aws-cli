**To get details about all active and terminated Automation executions**

This example describes all active and terminated Automation executions associated with your account.

Command::

  aws ssm describe-automation-executions

Output::

  {
    "AutomationExecutionMetadataList": [
        {
            "AutomationExecutionStatus": "Failed",
            "Outputs": {
                "createImage.ImageId": [
                    "No output available yet because the step is not successfully executed"
                ]
            },
            "DocumentName": "AWS-UpdateLinuxAmi",
            "AutomationExecutionId": "4105a4fc-f944-11e6-9d32-8fb2db27a909",
            "ExecutionEndTime": 1487798228.456,
            "DocumentVersion": "1",
            "ExecutionStartTime": 1487798222.746,
            "ExecutedBy": "admin"
        }
    ]
  }

**To get details of a specific Automation execution**

This example shows the details about Automation execution ID ``4105a4fc-f944-11e6-9d32-8fb2db27a909``.

Command::

   aws ssm get-automation-execution --automation-execution-id "4105a4fc-f944-11e6-9d32-8fb2db27a909"
   