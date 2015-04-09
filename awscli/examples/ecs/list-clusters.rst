**To list your available clusters**

This example command lists all of your available clusters in your default region.

Command::

  aws ecs list-clusters

Output::

	{
	    "clusterArns": [
	        "arn:aws:ecs:us-east-1:<aws_account_id>:cluster/test",
	        "arn:aws:ecs:us-east-1:<aws_account_id>:cluster/default"
	    ]
	}
