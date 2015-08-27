**To describe a cluster**

This example command provides a description of the specified cluster in your default region.

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
	            "clusterArn": "arn:aws:ecs:us-west-2:<aws_Account_id>:cluster/default"
	        }
	    ],
	    "failures": []
	}
