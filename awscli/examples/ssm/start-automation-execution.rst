**To initiate the execution of an Automation document**

This example runs the AWS-UpdateLinuxAMI document specifying an Automation role, an AMI source ID, and an Amazon EC2 instance role.

Command::

  aws ssm start-automation-execution --document-name "AWS-UpdateLinuxAmi" --parameters "AutomationAssumeRole=arn:aws:iam::809632081692:role/SSMAutomationRole,SourceAmiId=ami-f173cc91,InstanceIamRole=EC2InstanceRole"
  
Output::

  {
	"AutomationExecutionId": "4105a4fc-f944-11e6-9d32-8fb2db27a909"
  }
