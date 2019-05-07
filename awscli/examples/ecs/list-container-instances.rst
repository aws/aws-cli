**To list the container instances in a cluster**

The following example shows how to list all of the available container instances in a cluster.

Command::

  aws ecs list-container-instances --cluster MyCluster

Output::

	{
	    "containerInstanceArns": [
	        "arn:aws:ecs:us-west-2:123456789012:container-instance/MyCluster/f6bbb147-5370-4ace-8c73-c7181ded911f",
	        "arn:aws:ecs:us-west-2:123456789012:container-instance/MyCluster/ffe3d344-77e2-476c-a4d0-bf560ad50acb"
	    ]
	}
