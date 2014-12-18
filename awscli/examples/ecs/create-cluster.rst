**To create a new cluster**

This example command creates a cluster in your default region.

Command::

  aws ecs create-cluster --cluster-name "dev_preview"

Output::

	{
	    "cluster": {
	        "clusterName": "dev_preview",
	        "status": "ACTIVE",
	        "clusterArn": "arn:aws:ecs:us-west-2:<aws_account_id>:cluster/dev_preview"
	    }
	}
