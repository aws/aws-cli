**To list the registered task definitions**

The following example shows how to list all of the registered task definitions.

Command::

  aws ecs list-task-definitions

Output::

	{
	    "taskDefinitionArns": [
	        "arn:aws:ecs:us-west-2:123456789012:task-definition/sleep300:2",
	        "arn:aws:ecs:us-west-2:123456789012:task-definition/sleep360:1",
	        "arn:aws:ecs:us-west-2:123456789012:task-definition/wordpress:3",
	        "arn:aws:ecs:us-west-2:123456789012:task-definition/wordpress:4",
	        "arn:aws:ecs:us-west-2:123456789012:task-definition/wordpress:5",
	        "arn:aws:ecs:us-west-2:123456789012:task-definition/wordpress:6"
	    ]
	}

**To list the registered task definitions in a family**

The following example shows how to list the task definition revisions of a specified family.

Command::

  aws ecs list-task-definitions --family-prefix wordpress

Output::

	{
	    "taskDefinitionArns": [
	        "arn:aws:ecs:us-west-2:123456789012:task-definition/wordpress:3",
	        "arn:aws:ecs:us-west-2:123456789012:task-definition/wordpress:4",
	        "arn:aws:ecs:us-west-2:123456789012:task-definition/wordpress:5",
	        "arn:aws:ecs:us-west-2:123456789012:task-definition/wordpress:6"
	    ]
	}