**To describe a task definition**

This example command provides a description of the specified task definition.

Command::

  aws ecs describe-task-definition --task-definition wordpress:6

Output::

	{
	    "taskDefinition": {
	        "taskDefinitionArn": "arn:aws:ecs:us-west-2:<aws_account_id>:task-definition/wordpress:6",
	        "containerDefinitions": [
	            {
	                "environment": [
	                    {
	                        "name": "DB_USER",
	                        "value": "root"
	                    },
	                    {
	                        "name": "DB_PASS",
	                        "value": "pass"
	                    }
	                ],
	                "name": "wordpress",
	                "links": [
	                    "db"
	                ],
	                "image": "tutum/wordpress-stackable",
	                "essential": true,
	                "portMappings": [
	                    {
	                        "containerPort": 80,
	                        "hostPort": 80
	                    }
	                ],
	                "entryPoint": [
	                    "/bin/sh",
	                    "-c"
	                ],
	                "memory": 500,
	                "cpu": 10
	            },
	            {
	                "environment": [
	                    {
	                        "name": "MYSQL_ROOT_PASSWORD",
	                        "value": "pass"
	                    }
	                ],
	                "name": "db",
	                "image": "mysql",
	                "cpu": 10,
	                "portMappings": [],
	                "entryPoint": [
	                    "/entrypoint.sh"
	                ],
	                "memory": 500,
	                "essential": true
	            }
	        ],
	        "family": "wordpress",
	        "revision": 6
	    }
	}
