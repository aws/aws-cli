**To describe a task**

This example command provides a description of the specified task, using the task UUID as an identifier.

Command::

  aws ecs describe-tasks --tasks c5cba4eb-5dad-405e-96db-71ef8eefe6a8

Output::

	{
	    "failures": [],
	    "tasks": [
	        {
	            "taskArn": "arn:aws:ecs:<region>:<aws_account_id>:task/c5cba4eb-5dad-405e-96db-71ef8eefe6a8",
	            "overrides": {
	                "containerOverrides": [
	                    {
	                        "name": "ecs-demo"
	                    }
	                ]
	            },
	            "lastStatus": "RUNNING",
	            "containerInstanceArn": "arn:aws:ecs:<region>:<aws_account_id>:container-instance/18f9eda5-27d7-4c19-b133-45adc516e8fb",
	            "clusterArn": "arn:aws:ecs:<region>:<aws_account_id>:cluster/default",
	            "desiredStatus": "RUNNING",
	            "taskDefinitionArn": "arn:aws:ecs:<region>:<aws_account_id>:task-definition/amazon-ecs-sample:1",
	            "startedBy": "ecs-svc/9223370608528463088",
	            "containers": [
	                {
	                    "containerArn": "arn:aws:ecs:<region>:<aws_account_id>:container/7c01765b-c588-45b3-8290-4ba38bd6c5a6",
	                    "taskArn": "arn:aws:ecs:<region>:<aws_account_id>:task/c5cba4eb-5dad-405e-96db-71ef8eefe6a8",
	                    "lastStatus": "RUNNING",
	                    "name": "ecs-demo",
	                    "networkBindings": [
	                        {
	                            "bindIP": "0.0.0.0",
	                            "containerPort": 80,
	                            "hostPort": 80
	                        }
	                    ]
	                }
	            ]
	        }
	    ]
	}
