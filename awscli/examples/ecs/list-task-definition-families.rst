**To list the registered task definition families**

The following example shows how to list all of the registered task definition families.

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

**To filter the registered task definition families**

The following example shows how to list the task definition revisions that start with "hpcc".

Command::

  aws ecs list-task-definition-families --family-prefix hpcc

Output::

	{
	    "families": [
	        "hpcc",
	        "hpcc-c4-8xlarge"
	    ]
	}
