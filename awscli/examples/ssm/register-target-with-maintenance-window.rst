**To register a single target with a Maintenance Window**

This example registers an instance with a Maintenance Window.

Command::

  aws ssm register-target-with-maintenance-window --window-id "mw-ab12cd34ef56gh78" --target "Key=InstanceIds,Values=i-0000293ffd8c57862" --owner-information "Single instance" --resource-type "INSTANCE"

Output::

  {
	"WindowTargetId":"1a2b3c4d-1a2b-1a2b-1a2b-1a2b3c4d-1a2"
  }

**To register multiple targets with a Maintenance Window**
	
This example registers two instances with a Maintenance Window.

Command::

  aws ssm register-target-with-maintenance-window --window-id "mw-ab12cd34ef56gh78" --target "Key=InstanceIds,Values=i-0000293ffd8c57862,i-0cb2b964d3e14fd9f" --owner-information "Two instances in a list" --resource-type "INSTANCE"

**To register a target with a Maintenance Window using EC2 tags**

This example registers an instance with a Maintenance Window using EC2 tags.

Command::

  aws ssm register-target-with-maintenance-window --window-id "mw-06cf17cbefcb4bf4f" --targets "Key=tag:Environment,Values=Prod" "Key=Role,Values=Web" --owner-information "Production Web Servers" --resource-type "INSTANCE"
