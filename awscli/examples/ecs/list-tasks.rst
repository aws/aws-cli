**To list the tasks in a cluster**

This example command lists all of the tasks in a cluster.

Command::

  aws ecs list-tasks --cluster default

Output::

	{
	    "taskArns": [
	        "arn:aws:ecs:us-east-1:<aws_account_id>:task/0cc43cdb-3bee-4407-9c26-c0e6ea5bee84",
	        "arn:aws:ecs:us-east-1:<aws_account_id>:task/6b809ef6-c67e-4467-921f-ee261c15a0a1"
	    ]
	}

**To list the tasks on a particular container instance**

This example command lists the tasks of a specified container instance, using the container instance UUID as a filter.

Command::

  aws ecs list-tasks --cluster default --container-instance f6bbb147-5370-4ace-8c73-c7181ded911f

Output::

	{
	    "taskArns": [
	        "arn:aws:ecs:us-east-1:<aws_account_id>:task/0cc43cdb-3bee-4407-9c26-c0e6ea5bee84"
	    ]
	}