**To register a task with a maintenance window**

This example registers a task to a maintenance window which is targeted at an instance.

Command::

  aws ssm register-task-with-maintenance-window --window-id "mw-ab12cd34ef56gh78" --task-arn "AWS-RunShellScript" --targets "Key=InstanceIds,Values=i-0000293ffd8c57862" --service-role-arn "arn:aws:iam::812345678901:role/MaintenanceWindowsRole" --task-type "RUN_COMMAND" --task-parameters "{\"commands\":{\"Values\":[\"df\"]}}" --max-concurrency 1 --max-errors 1 --priority 10
  
Output::

  {
	"WindowTaskId":"44444444-5555-6666-7777-88888888"
  }
	
**To register a task using a Maintenance Windows target ID**
	
This example registers a task using a maintenance window target ID. The maintenance window target ID was in the output of the ``aws ssm register-target-with-maintenance-window`` command, otherwise you can retrieve it from the output of the ``aws ssm describe-maintenance-window-targets`` command.

Command::

  aws ssm register-task-with-maintenance-window --targets "Key=WindowTargetIds,Values=350d44e6-28cc-44e2-951f-4b2c985838f6" --task-arn "AWS-RunShellScript" --service-role-arn "arn:aws:iam::812345678901:role/MaintenanceWindowsRole" --window-id "mw-ab12cd34ef56gh78" --task-type "RUN_COMMAND" --task-parameters  "{\"commands\":{\"Values\":[\"df\"]}}" --max-concurrency 1 --max-errors 1 --priority 10
  