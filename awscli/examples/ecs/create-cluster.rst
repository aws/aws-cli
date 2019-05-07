**To create a new cluster**

The following example shows how to create a cluster.

Command::

  aws ecs create-cluster --cluster-name MyCluster

Output::

	{
	    "cluster": {
	        "clusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/MyCluster",
	        "clusterName": "MyCluster",
	        "status": "ACTIVE",
	        "registeredContainerInstancesCount": 0,
	        "pendingTasksCount": 0,
	        "runningTasksCount": 0,
	        "activeServicesCount": 0,
	        "statistics": [],
            "tags": []
	    }
	}

**To create a new cluster with multiple tags**

The following example shows how to create a cluster with multiple tags.

Command::

  aws ecs create-cluster --cluster-name MyCluster --tags key=key1,value=value1 key=key2,value=value2 key=key3,value=value3

Output::

	{
	    "cluster": {
	        "clusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/MyCluster",
	        "clusterName": "MyCluster",
	        "status": "ACTIVE",
	        "registeredContainerInstancesCount": 0,
	        "pendingTasksCount": 0,
	        "runningTasksCount": 0,
	        "activeServicesCount": 0,
	        "statistics": [],
            "tags": [
            	{
                	"key": "key1",
                	"value": "value1"
            	},
            	{
             	   "key": "key2",
             	   "value": "value2"
            	},
            	{
             	   "key": "key3",
             	   "value": "value3"
            	}
            ]
	    }
	}