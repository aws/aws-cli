**To list your available clusters**

The following example shows how to list all of the available clusters.

Command::

  aws ecs list-clusters

Output::

	{
	    "clusterArns": [
	        "arn:aws:ecs:us-west-2:123456789012:cluster/test",
	        "arn:aws:ecs:us-west-2:123456789012:cluster/default"
	    ]
	}
