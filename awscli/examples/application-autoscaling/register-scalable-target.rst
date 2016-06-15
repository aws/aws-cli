**To register a new scalable target**

This example command registers a scalable target from an Amazon ECS service called `web-app` that is running on the `default` cluster, with a minimum desired count of 1 task and a maximum desired count of 10 tasks.

Command::

  aws application-autoscaling register-scalable-target --resource-id service/default/web-app --service-namespace ecs --scalable-dimension ecs:service:DesiredCount --min-capacity 1 --max-capacity 10 --role-arn arn:aws:iam::012345678910:role/ApplicationAutoscalingECSRole

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
