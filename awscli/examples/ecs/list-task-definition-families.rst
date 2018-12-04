**To list your registered task definition families**

This example command lists all of your registered task definition families.

Command::

  aws ecs list-task-definition-families

Output::

	{
	    "families": [
	        "node-js-app",
	        "web-timer",
	        "hpcc",
	        "hpcc-c4-8xlarge"
	    ]
	}

**To filter your registered task definition families**

This example command lists the task definition revisions that start with "hpcc".

Command::

  aws ecs list-task-definition-families --family-prefix hpcc

Output::

	{
	    "families": [
	        "hpcc",
	        "hpcc-c4-8xlarge"
	    ]
	}
