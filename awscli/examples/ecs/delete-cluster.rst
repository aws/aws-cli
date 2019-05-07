**To delete an empty cluster**

The following example shows how to delete an empty cluster.

Command::

  aws ecs delete-cluster --cluster MyCluster

Output::

	{
	    "cluster": {
	        "clusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/MyCluster",
	        "status": "INACTIVE",
	        "clusterName": "MyCluster",
	        "registeredContainerInstancesCount": 0,
	        "pendingTasksCount": 0,
	        "runningTasksCount": 0,
			"activeServicesCount": 0
			"statistics": [],
        	"tags": []
	    }
	}
