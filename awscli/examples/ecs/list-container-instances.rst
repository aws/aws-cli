**To list your available container instances in a cluster**

This example command lists all of your available container instances in the specified cluster (`my_cluster`) in your default region.

Command::

  aws ecs list-container-instances --cluster my_cluster

Output::

	{
	    "containerInstanceArns": [
	        "arn:aws:ecs:us-east-1:<aws_account_id>:container-instance/f6bbb147-5370-4ace-8c73-c7181ded911f",
	        "arn:aws:ecs:us-east-1:<aws_account_id>:container-instance/ffe3d344-77e2-476c-a4d0-bf560ad50acb"
	    ]
	}
