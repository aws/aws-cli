**To create a new service**

This example command creates a service in your default region called ``ecs-simple-service``. The service uses the ``ecs-demo`` task definition and it maintains 10 instantiations of that task.

Command::

  aws ecs create-service --service-name ecs-simple-service --task-definition ecs-demo --desired-count 10

Output::

	{
	    "service": {
	        "status": "ACTIVE",
	        "taskDefinition": "arn:aws:ecs:<region>:<aws_account_id>:task-definition/ecs-demo:1",
	        "pendingCount": 0,
	        "loadBalancers": [],
	        "desiredCount": 10,
	        "serviceName": "ecs-simple-service",
	        "clusterArn": "arn:aws:ecs:<region>:<aws_account_id>:cluster/default",
	        "serviceArn": "arn:aws:ecs:<region>:<aws_account_id>:service/ecs-simple-service",
	        "deployments": [
	            {
	                "status": "PRIMARY",
	                "pendingCount": 0,
	                "createdAt": 1428096748.604,
	                "desiredCount": 10,
	                "taskDefinition": "arn:aws:ecs:<region>:<aws_account_id>:task-definition/ecs-demo:1",
	                "updatedAt": 1428096748.604,
	                "id": "ecs-svc/<deployment_id>",
	                "runningCount": 0
	            }
	        ],
	        "events": [],
	        "runningCount": 0
	    }
	}

	
**To create a new service behind a load balancer**

This example command creates a service in your default region called ``ecs-simple-service-elb``. The service uses the ``ecs-demo`` task definition and it maintains 10 instantiations of that task. You must have a load balancer configured in the same region as your container instances.

This example uses the ``--cli-input-json`` option and a JSON input file called ``ecs-simple-service-elb.json`` with the below format.

Input file::

    {
        "serviceName": "ecs-simple-service-elb",
        "taskDefinition": "ecs-demo",
        "loadBalancers": [
            {
                "loadBalancerName": "EC2Contai-EcsElast-S06278JGSJCM",
                "containerName": "simple-demo",
                "containerPort": 80
            }
        ],
        "desiredCount": 10,
        "role": "ecsServiceRole"
    }

Command::

  aws ecs create-service --service-name ecs-simple-service-elb --cli-input-json file://ecs-simple-service-elb.json

Output::

	{
	    "service": {
	        "status": "ACTIVE",
	        "taskDefinition": "arn:aws:ecs:<region>:<aws_account_id>:task-definition/ecs-demo:1",
	        "pendingCount": 0,
	        "loadBalancers": [
	            {
	                "containerName": "ecs-demo",
	                "containerPort": 80,
	                "loadBalancerName": "EC2Contai-EcsElast-S06278JGSJCM"
	            }
	        ],
	        "roleArn": "arn:aws:iam::<aws_account_id>:role/ecsServiceRole",
	        "desiredCount": 10,
	        "serviceName": "ecs-simple-service-elb",
	        "clusterArn": "arn:aws:ecs:<region>:<aws_account_id>:cluster/default",
	        "serviceArn": "arn:aws:ecs:<region>:<aws_account_id>:service/ecs-simple-service-elb",
	        "deployments": [
	            {
	                "status": "PRIMARY",
	                "pendingCount": 0,
	                "createdAt": 1428100239.123,
	                "desiredCount": 10,
	                "taskDefinition": "arn:aws:ecs:<region>:<aws_account_id>:task-definition/ecs-demo:1",
	                "updatedAt": 1428100239.123,
	                "id": "ecs-svc/<deployment_id>",
	                "runningCount": 0
	            }
	        ],
	        "events": [],
	        "runningCount": 0
	    }
	}