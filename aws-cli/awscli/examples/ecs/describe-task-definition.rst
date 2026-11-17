**To describe a task definition**

The following ``describe-task-definition`` example retrieves the details of a task definition. ::

    aws ecs describe-task-definition \
        --task-definition hello_world:8

Output::

    {
        "taskDefinition": {
            "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/hello_world:8",
            "containerDefinitions": [
                {
                    "cpu": 10,
                    "environment": [],
                    "essential": true,
                    "image": "wordpress",
                    "links": [
                        "mysql"
                    ] ,
                    "memory": 500,
                    "mountPoints": [],
                    "name": "wordpress",
                    "portMappings": [
                        {
                            "containerPort": 80,
                            "hostPort": 80
                        }
                    ],
                    "volumesFrom": []
                },
                {
                    "cpu": 10,
                    "environment": [
                        {
                            "name": "MYSQL_ROOT_PASSWORD",
                            "value": "password"
                        }
                    ],
                    "essential": true,
                    "image": "mysql",
                    "memory": 500,
                    "mountPoints": [],
                    "name": "mysql",
                    "portMappings": [],
                    "volumesFrom": []
                }
            ],
        "family": "hello_world",
        "revision": 8,
        "volumes": [],
        "status": "ACTIVE",
        "placementConstraints": [],
        "compatibilities": [
            "EXTERNAL",
            "EC2"
        ],
        "registeredAt": "2024-06-21T11:15:12.669000-05:00",
        "registeredBy": "arn:aws:sts::123456789012:assumed-role/demo-role/jane-doe"
        },
        "tags": []
    }

For more information, see `Amazon ECS task definitions <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html>`__ in the *Amazon ECS Developer Guide*.
