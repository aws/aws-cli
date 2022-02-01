**Example 1: To register a task definition with a JSON file**

The following ``register-task-definition`` example registers a task definition to the specified family with container definitions that are saved in JSON format at the specified file location. ::

    aws ecs register-task-definition \
        --cli-input-json file://<path_to_json_file>/sleep360.json

``sleep360.json`` file contents::

    {
        "containerDefinitions": [
            {
                "name": "sleep",
                "image": "busybox",
                "cpu": 10,
                "command": [
                    "sleep",
                    "360"
                ],
                "memory": 10,
                "essential": true
            }
        ],
        "family": "sleep360"
    }

Output::

    {
        "taskDefinition": {
            "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/sleep360:2",
            "containerDefinitions": [
                {
                    "name": "sleep",
                    "image": "busybox",
                    "cpu": 10,
                    "memory": 10,
                    "portMappings": [],
                    "essential": true,
                    "command": [
                        "sleep",
                        "360"
                    ],
                    "environment": [],
                    "mountPoints": [],
                    "volumesFrom": []
                }
            ],
            "family": "sleep360",
            "revision": 2,
            "volumes": [],
            "status": "ACTIVE",
            "placementConstraints": [],
            "compatibilities": [
                "EC2"
            ]
        }
    }

**Example 2: To register a task definition with a JSON string parameter**

The following ``register-task-definition`` example registers the same task definition from the previous example, but the container definitions are provided as a string parameter with the double quotes escaped. ::

    aws ecs register-task-definition \
        --family sleep360 \
        --container-definitions "[{\"name\":\"sleep\",\"image\":\"busybox\",\"cpu\":10,\"command\":[\"sleep\",\"360\"],\"memory\":10,\"essential\":true}]"

The output is identical to the previous example.

**Example 3: To use data volumes in a task definition**

This example task definition file creates a data volume called `webdata` that exists at `/ecs/webdata` on the container instance. The volume is mounted read-only as `/usr/share/nginx/html` on the `web` container, and read-write as `/nginx/` on the `timer` container. ::

    {
        "family": "web-timer",
        "containerDefinitions": [
            {
                "name": "web",
                "image": "nginx",
                "cpu": 99,
                "memory": 100,
                "portMappings": [
                    {
                        "containerPort": 80,
                        "hostPort": 80
                    }
                ],
                "essential": true,
                "mountPoints": [
                    {
                        "sourceVolume": "webdata",
                        "containerPath": "/usr/share/nginx/html",
                        "readOnly": true
                    }
                ]
            }, 
            {
                "name": "timer",
                "image": "busybox",
                "cpu": 10,
                "memory": 20,
                "entryPoint": ["sh", "-c"],
                "command": ["while true; do date > /nginx/index.html; sleep 1; done"],
                "mountPoints": [
                    {
                        "sourceVolume": "webdata",
                        "containerPath": "/nginx/"
                    }
                ]
            }
        ],
        "volumes": [
            {
                "name": "webdata", 
                "host": {
                    "sourcePath": "/ecs/webdata"
                }
            }
        ]
    }


For more information, see `Creating a Task Definition <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-task-definition.html>`_ in the *Amazon ECS Developer Guide*.
