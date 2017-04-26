**To display the details of an Automation Execution**

This example displays the details of an Automation Execution.

Command::

  aws ssm get-automation-execution --automation-execution-id "4105a4fc-f944-11e6-9d32-8fb2db27a909"

Output::

  {
    "AutomationExecution": {
        "AutomationExecutionStatus": "Failed",
        "Parameters": {
            "SourceAmiId": [
                "ami-f173cc91"
            ],
            "AutomationAssumeRole": [
                "arn:aws:iam::812345678901:role/SSMAutomationRole"
            ],
            "InstanceIamRole": [
                "EC2InstanceRole"
            ]
        },
        "Outputs": {
            "createImage.ImageId": [
                "No output available yet because the step is not successfully executed"
            ]
        },
        "DocumentName": "AWS-UpdateLinuxAmi",
        "AutomationExecutionId": "4105a4fc-f944-11e6-9d32-8fb2db27a909",
        "FailureMessage": "Step launchInstance failed maximum allowed times. You are not authorized to perform this operation. Encoded authorization failure message: --truncated-- (Service: AmazonEC2; Status Code: 403; Error Code: UnauthorizedOperation; Request ID: 6a002f94-ba37-43fd-99e6-39517715fce5)",
        "ExecutionEndTime": 1487798228.456,
        "DocumentVersion": "1",
        "ExecutionStartTime": 1487798222.746,
        "StepExecutions": [
            {
                "Inputs": {
                    "MaxInstanceCount": "1",
                    "UserData": "\"--truncated--\"",
                    "MinInstanceCount": "1",
                    "ImageId": "\"ami-f173cc91\"",
                    "IamInstanceProfileName": "\"EC2InstanceRole\"",
                    "InstanceType": "\"t2.micro\""
                },
                "StepName": "launchInstance",
                "FailureMessage": "Step launchInstance failed maximum allowed times. You are not authorized to perform this operation. Encoded authorization failure message: --truncated--)",
                "ExecutionEndTime": 1487798226.014,
                "ExecutionStartTime": 1487798223.346,
                "Action": "aws:runInstances",
                "StepStatus": "Failed"
            },
            {
                "Action": "aws:runCommand",
                "StepName": "updateOSSoftware",
                "StepStatus": "Pending"
            },
            {
                "Action": "aws:changeInstanceState",
                "StepName": "stopInstance",
                "StepStatus": "Pending"
            },
            {
                "Action": "aws:createImage",
                "StepName": "createImage",
                "StepStatus": "Pending"
            },
            {
                "Action": "aws:changeInstanceState",
                "StepName": "terminateInstance",
                "StepStatus": "Pending"
            }
        ]
    }
  }
  