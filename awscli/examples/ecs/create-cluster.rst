**To create a new cluster**

This example command creates a cluster in your default region.

Command::

  aws ecs create-cluster --cluster-name "my_cluster"

Output::

	{
	    "cluster": {
	        "clusterName": "my_cluster",
	        "status": "ACTIVE",
	        "clusterArn": "arn:aws:ecs:us-west-2:<aws_account_id>:cluster/my_cluster"
	    }
	}
