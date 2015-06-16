**To create a new cluster**

This example command creates a cluster in your default region.

Command::

  aws ecs create-cluster --cluster-name "my_cluster"

Output::

	{
	    "cluster": {
	        "status": "ACTIVE",
	        "clusterName": "my_cluster",
	        "registeredContainerInstancesCount": 0,
	        "pendingTasksCount": 0,
	        "runningTasksCount": 0,
	        "activeServicesCount": 0,
	        "clusterArn": "arn:aws:ecs:<region>:<aws_account_id>:cluster/my_cluster"
	    }
	}
