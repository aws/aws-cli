**To describe a task definition**

This example command provides a description of the specified task definition.

Command::

  aws ecs describe-task-definition --task-definition hello_world:8

Output::

	{
	    "taskDefinition": {
	        "volumes": [],
	        "taskDefinitionArn": "arn:aws:ecs:us-east-1:<aws_account_id>:task-definition/hello_world:8",
	        "containerDefinitions": [
	            {
	                "environment": [],
	                "name": "wordpress",
	                "links": [
	                    "mysql"
	                ],
	                "mountPoints": [],
	                "image": "wordpress",
	                "essential": true,
	                "portMappings": [
	                    {
	                        "containerPort": 80,
	                        "hostPort": 80
	                    }
	                ],
	                "memory": 500,
	                "cpu": 10,
	                "volumesFrom": []
	            },
	            {
	                "environment": [
	                    {
	                        "name": "MYSQL_ROOT_PASSWORD",
	                        "value": "password"
	                    }
	                ],
	                "name": "mysql",
	                "mountPoints": [],
	                "image": "mysql",
	                "cpu": 10,
	                "portMappings": [],
	                "memory": 500,
	                "essential": true,
	                "volumesFrom": []
	            }
	        ],
	        "family": "hello_world",
	        "revision": 8
	    }
	}
