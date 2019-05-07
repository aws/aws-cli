**To describe a cluster**

The following example shows how to describe a cluster.

Command::

  aws ecs describe-clusters --cluster default

Output::

	{
	    "clusters": [
	        {
	            "status": "ACTIVE",
	            "clusterName": "default",
	            "registeredContainerInstancesCount": 0,
	            "pendingTasksCount": 0,
	            "runningTasksCount": 0,
	            "activeServicesCount": 1,
	            "clusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/default"
	        }
	    ],
	    "failures": []
	}
