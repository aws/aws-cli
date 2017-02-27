**To register a task with a maintenance window**

This example registers a task, which uses Systems Manager Run Command to execute the ``df`` command using the ``AWS-RunShellScript`` document, to Maintenance Window ``mw-ab12cd34ef56gh78`` which is targeted at Instance Id ``i-0000293ffd8c57862``.

Command::

  aws ssm register-task-with-maintenance-window --window-id "mw-ab12cd34ef56gh78" --task-arn "AWS-RunShellScript" --targets "Key=InstanceIds,Values=i-0000293ffd8c57862" --service-role-arn "arn:aws:iam::<aws_account_id>:role/MaintenanceWindowsRole" --task-type "RUN_COMMAND" --task-parameters "{\"commands\":{\"Values\":[\"df\"]}}" --max-concurrency 1 --max-errors 1 --priority 10
  
Output::

  {
	"WindowTaskId":"44444444-5555-6666-7777-88888888"
  }
	
**To register a task using a Maintenance Windows target ID**
	
This example registers a task using a Maintenance Window target ID. The Maintenance Window target ID was in the output of the ``aws ssm register-target-with-maintenance-window`` command, otherwise you can retrieve it from the output of the ``aws ssm describe-maintenance-window-targets`` command.

Command::

  aws ssm register-task-with-maintenance-window --targets "Key=WindowTargetIds,Values=350d44e6-28cc-44e2-951f-4b2c985838f6" --task-arn "AWS-RunShellScript" --service-role-arn "arn:aws:iam::<aws_account_id>:role/MaintenanceWindowsRole" --window-id "mw-ab12cd34ef56gh78" --task-type "RUN_COMMAND" --task-parameters  "{\"commands\":{\"Values\":[\"df\"]}}" --max-concurrency 1 --max-errors 1 --priority 10
  