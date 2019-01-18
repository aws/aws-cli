**To register an Automation task with a Maintenance Window**

This example registers an Automation task with a Maintenance Window that is targeted at an instance.

Command::

   aws ssm register-task-with-maintenance-window --window-id "mw-082dcd7649dee04e4" --targets Key=InstanceIds,Values=i-12345201220f8cd0d --task-arn AWS-RestartEC2Instance --service-role-arn arn:aws:iam::111222333444:role/SSM --task-type AUTOMATION --task-invocation-parameters "{\"Automation\":{\"DocumentVersion\":\"\$LATEST\",\"Parameters\":{\"InstanceId\":[\"{{TARGET_ID}}\"]}}}" --priority 0 --max-concurrency 1 --max-errors 1 --name "AutomationExample" --description "Restarting EC2 Instance for maintenance"
  
Output::

  {
	"WindowTaskId":"11144444-5555-6666-7777-88888888"
  }
  
**To register a Lambda task with a Maintenance Window**

This example registers a Lambda task with a Maintenance Window that is targeted at an instance.

Command::

   aws ssm register-task-with-maintenance-window --window-id "mw-082dcd7649dee04e4" --targets Key=InstanceIds,Values=i-12344d305eea74171 --task-arn arn:aws:lambda:us-east-1:111222333444:function:SSMTestLAMBDA --service-role-arn arn:aws:iam::111222333444:role/SSM --task-type LAMBDA --task-invocation-parameters '{"Lambda":{"Payload":"{\"targetId\":\"{{TARGET_ID}}\",\"targetType\":\"{{TARGET_TYPE}}\"}","Qualifier":"$LATEST"}}' --priority 0 --max-concurrency 10 --max-errors 5 --name "Lambda_Example" --description "My Lambda Example"
  
Output::

  {
	"WindowTaskId":"22244444-5555-6666-7777-88888888"
  }

**To register a Run Command task with a Maintenance Window**

This example registers a Run Command task with a Maintenance Window that is targeted at an instance.

Command::

  aws ssm register-task-with-maintenance-window --window-id "mw-082dcd7649dee04e4" --targets "Key=InstanceIds,Values=i-12344d305eea74171" --service-role-arn "arn:aws:iam::111222333444:role/SSM" --task-type "RUN_COMMAND" --name "SSMInstallPowerShellModule" --task-arn "AWS-InstallPowerShellModule" --task-invocation-parameters "{\"RunCommand\":{\"Comment\":\"\",\"OutputS3BucketName\":\"runcommandlogs\",\"Parameters\":{\"commands\":[\"Get-Module -ListAvailable\"],\"executionTimeout\":[\"3600\"],\"source\":[\"https:\/\/gallery.technet.microsoft.com\/EZOut-33ae0fb7\/file\/110351\/1\/EZOut.zip\"],\"workingDirectory\":[\"\\\\\"]},\"TimeoutSeconds\":600}}" --max-concurrency 1 --max-errors 1 --priority 10
  
Output::

  {
	"WindowTaskId":"33344444-5555-6666-7777-88888888"
  }

**To register a Step Functions task with a Maintenance Window**

This example registers a Step Functions task with a Maintenance Window that is targeted at an instance.

Command::

   aws ssm register-task-with-maintenance-window --window-id "mw-1234d787d641f11f3" --targets Key=WindowTargetIds,Values=12347414-69c3-49f8-95b8-ed2dcf045faa --task-arn arn:aws:states:us-east-1:111222333444:stateMachine:SSMTestStateMachine --service-role-arn arn:aws:iam::111222333444:role/MaintenanceWindows --task-type STEP_FUNCTIONS --task-invocation-parameters '{"StepFunctions":{"Input":"{\"instanceId\":\"{{TARGET_ID}}\"}"}}' --priority 0 --max-concurrency 10 --max-errors 5 --name "Step_Functions_Example" --description "My Step Functions Example"
  
Output::

  {
	"WindowTaskId":"44444444-5555-6666-7777-88888888"
  }
	
**To register a task using a Maintenance Windows target ID**
	
This example registers a task using a Maintenance Window target ID. The maintenance window target ID was in the output of the ``aws ssm register-target-with-maintenance-window`` command, otherwise you can retrieve it from the output of the ``aws ssm describe-maintenance-window-targets`` command.

Command::

  aws ssm register-task-with-maintenance-window --targets "Key=WindowTargetIds,Values=350d44e6-28cc-44e2-951f-4b2c985838f6" --task-arn "AWS-RunShellScript" --service-role-arn "arn:aws:iam::812345678901:role/MaintenanceWindowsRole" --window-id "mw-ab12cd34ef56gh78" --task-type "RUN_COMMAND" --task-parameters  "{\"commands\":{\"Values\":[\"df\"]}}" --max-concurrency 1 --max-errors 1 --priority 10
  
