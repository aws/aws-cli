**To initiate the execution of an Automation document**

This example executes a document.

Command::

  aws ssm start-automation-execution --document-name "AWS-UpdateLinuxAmi" --parameters "AutomationAssumeRole=arn:aws:iam::123456789012:role/SSMAutomationRole,SourceAmiId=ami-f1730123,IamInstanceProfileName=EC2InstanceRole"
  
Output::

  {
	"AutomationExecutionId": "4105a4fc-f944-11e6-9d32-0a1b2c3d495h"
  }

**To initiate the execution of an Automation document in multiple accounts**

This example restarts Amazon EC2 instances in the 1a2b3c4d5e6f7g8h and a1b2c3d4e5f6h7 accounts, which are located in the us-east-2 and us-west-1 Regions. The instances must be tagged with Env-PROD.

Command::

  aws ssm start-automation-execution --document-name AWS-RestartEC2Instance --parameters AutomationAssumeRole=arn:aws:iam::123456789012:role/AWS-SystemsManager-AutomationAdministrationRole --target-parameter-name InstanceId --targets Key=tag:Env,Values=PROD --target-locations Accounts=1a2b3c4d5e6f7g8h,a1b2c3d4e5f6h7,Regions=us-east-2,us-west-1,ExecutionRoleName=AWS-SystemsManager-AutomationExecutionRole
  
Output::

  {
	"AutomationExecutionId": "4105a4fc-f944-11e6-9d32-0a1b2c3d495h"
  }
