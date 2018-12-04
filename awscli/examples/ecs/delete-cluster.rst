**To delete an empty cluster**

This example command deletes an empty cluster in your default region.

Command::

  aws ecs delete-cluster --cluster my_cluster

Output::

	{
	    "cluster": {
	        "status": "INACTIVE",
	        "clusterName": "my_cluster",
	        "registeredContainerInstancesCount": 0,
	        "pendingTasksCount": 0,
	        "runningTasksCount": 0,
			"activeServicesCount": 0,
	        "clusterArn": "arn:aws:ecs:<region>:<aws_account_id>:cluster/my_cluster"
	    }
	}
