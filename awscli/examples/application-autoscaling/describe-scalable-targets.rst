**To describe scalable targets**

This example command describes the scalable targets for the `ecs` service namespace.

Command::

  aws application-autoscaling describe-scalable-targets --service-namespace ecs

Output::

	{
	    "ScalableTargets": [
	        {
	            "ScalableDimension": "ecs:service:DesiredCount",
	            "ResourceId": "service/default/web-app",
	            "RoleARN": "arn:aws:iam::012345678910:role/ApplicationAutoscalingECSRole",
	            "CreationTime": 1462558906.199,
	            "MinCapacity": 1,
	            "ServiceNamespace": "ecs",
	            "MaxCapacity": 10
	        }
	    ]
	}
