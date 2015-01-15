**To delete an empty cluster**

This example command deletes an empty cluster in your default region.

Command::

  aws ecs delete-cluster --cluster default

Output::

	{
	    "cluster": {
	        "clusterName": "default",
	        "status": "INACTIVE",
	        "clusterArn": "arn:aws:ecs:<region>:<aws_account_id>:cluster/default"
	    }
	}
