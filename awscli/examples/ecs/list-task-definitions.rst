**To list your registered task definitions**

This example command lists all of your registered task definitions.

Command::

  aws ecs list-task-definitions

Output::

	{
	    "taskDefinitionArns": [
	        "arn:aws:ecs:us-east-1:<aws_account_id>:task-definition/sleep300:2",
	        "arn:aws:ecs:us-east-1:<aws_account_id>:task-definition/sleep360:1",
	        "arn:aws:ecs:us-east-1:<aws_account_id>:task-definition/wordpress:3",
	        "arn:aws:ecs:us-east-1:<aws_account_id>:task-definition/wordpress:4",
	        "arn:aws:ecs:us-east-1:<aws_account_id>:task-definition/wordpress:5",
	        "arn:aws:ecs:us-east-1:<aws_account_id>:task-definition/wordpress:6"
	    ]
	}

**To list the registered task definitions in a family**

This example command lists the task definition revisions of a specified family.

Command::

  aws ecs list-task-definitions --family-prefix wordpress

Output::

	{
	    "taskDefinitionArns": [
	        "arn:aws:ecs:us-east-1:<aws_account_id>:task-definition/wordpress:3",
	        "arn:aws:ecs:us-east-1:<aws_account_id>:task-definition/wordpress:4",
	        "arn:aws:ecs:us-east-1:<aws_account_id>:task-definition/wordpress:5",
	        "arn:aws:ecs:us-east-1:<aws_account_id>:task-definition/wordpress:6"
	    ]
	}