**To register a task definition with a JSON file**

This example registers a task definition to the specified family with container definitions that are saved in JSON format at the specified file location.

Command::

  aws ecs register-task-definition --family sleep360 --container-definitions file://<path_to_json_file>/sleep360.json

JSON file format::

  [
    {
      "environment": [],
      "name": "sleep",
      "image": "busybox",
      "cpu": 10,
      "portMappings": [],
      "memory": 10,
      "command": [
        "sleep",
        "360"
      ],
      "essential": true
    }
  ]

Output::

	{
	    "taskDefinition": {
	        "taskDefinitionArn": "arn:aws:ecs:us-east-1:<aws_account_id>:task-definition/sleep360:1",
	        "containerDefinitions": [
	            {
	                "environment": [],
	                "name": "sleep",
	                "image": "busybox",
	                "cpu": 10,
	                "portMappings": [],
	                "command": [
	                    "sleep",
	                    "360"
	                ],
	                "memory": 10,
	                "essential": true
	            }
	        ],
	        "family": "sleep360",
	        "revision": 15
	    }
	}

**To register a task definition with a JSON string**

This example registers a the same task definition from the previous example, but the container definitions are in a string format with the double quotes escaped.

Command::

  aws ecs register-task-definition --family sleep360 --container-definitions "[{\"environment\":[],\"name\":\"sleep\",\"image\":\"busybox\",\"cpu\":10,\"portMappings\":[],\"memory\":10,\"command\":[\"sleep\",\"360\"],\"essential\":true}]"

Output::

	{
	    "taskDefinition": {
	        "taskDefinitionArn": "arn:aws:ecs:us-east-1:<aws_account_id>:task-definition/sleep360:15",
	        "containerDefinitions": [
	            {
	                "environment": [],
	                "name": "sleep",
	                "image": "busybox",
	                "cpu": 10,
	                "portMappings": [],
	                "command": [
	                    "sleep",
	                    "360"
	                ],
	                "memory": 10,
	                "essential": true
	            }
	        ],
	        "family": "sleep360",
	        "revision": 15
	    }
	}
