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
      "entryPoint": [
        "/bin/sh"
      ],
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
	        "taskDefinitionArn": "arn:aws:ecs:us-west-2:<aws_account_id>:task-definition/sleep360:2",
	        "containerDefinitions": [
	            {
	                "environment": [],
	                "name": "sleep",
	                "image": "busybox",
	                "cpu": 10,
	                "portMappings": [],
	                "entryPoint": [
	                    "/bin/sh"
	                ],
	                "memory": 10,
	                "command": [
	                    "sleep",
	                    "360"
	                ],
	                "essential": true
	            }
	        ],
	        "family": "sleep360",
	        "revision": 2
	    }
	}

**To register a task definition with a JSON string**

This example registers a the same task definition from the previous example, but the container definitions are in a string format with the double quotes escaped.

Command::

  aws ecs register-task-definition --family sleep360 --container-definitions "[{\"environment\":[],\"name\":\"sleep\",\"image\":\"busybox\",\"cpu\":10,\"portMappings\":[],\"entryPoint\":[\"/bin/sh\"],\"memory\":10,\"command\":[\"sleep\",\"360\"],\"essential\":true}]"

Output::

	{
	    "taskDefinition": {
	        "taskDefinitionArn": "arn:aws:ecs:us-west-2:<aws_account_id>:task-definition/sleep360:3",
	        "containerDefinitions": [
	            {
	                "environment": [],
	                "name": "sleep",
	                "image": "busybox",
	                "cpu": 10,
	                "portMappings": [],
	                "entryPoint": [
	                    "/bin/sh"
	                ],
	                "memory": 10,
	                "command": [
	                    "sleep",
	                    "360"
	                ],
	                "essential": true
	            }
	        ],
	        "family": "sleep360",
	        "revision": 3
	    }
	}
