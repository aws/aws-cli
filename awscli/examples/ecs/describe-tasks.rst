**To describe a task**

The following ``describe-tasks`` example retrieves the details of a task. You can specify the task by using either the ID or full ARN of the task. ::

    aws ecs describe-tasks \
        --cluster MyCluster \
        --tasks arn:aws:ecs:us-west-2:123456789012:task/MyCluster/1234567890123456789

Output::

    {
        "tasks": [
            {
                "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/MyCluster/1234567890123456789",
                "clusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/MyCluster",
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/sample-fargate:2",
                "overrides": {
                    "containerOverrides": [
                        {
                            "name": "fargate-app"
                        }
                    ]
                },
                "lastStatus": "RUNNING",
                "desiredStatus": "RUNNING",
                "cpu": "256",
                "memory": "512",
                "containers": [
                    {
                        "containerArn": "arn:aws:ecs:us-west-2:123456789012:container/a1b2c3d4-5678-90ab-cdef-11111EXAMPLE",
                        "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/MyCluster/1234567890123456789",
                        "name": "fargate-app",
                        "lastStatus": "RUNNING",
                        "networkBindings": [],
                        "networkInterfaces": [
                            {
                                "attachmentId": "a1b2c3d4-5678-90ab-cdef-22222EXAMPLE",
                                "privateIpv4Address": "10.0.0.4"
                            }
                        ],
                        "healthStatus": "UNKNOWN",
                        "cpu": "0"
                    }
                ],
                "startedBy": "ecs-svc/1234567890123456789",
                "version": 3,
                "connectivity": "CONNECTED",
                "connectivityAt": 1557134016.971,
                "pullStartedAt": 1557134025.379,
                "pullStoppedAt": 1557134033.379,
                "createdAt": 1557134011.644,
                "startedAt": 1557134035.379,
                "group": "service:fargate-service",
                "launchType": "FARGATE",
                "platformVersion": "1.3.0",
                "attachments": [
                    {
                        "id": "a1b2c3d4-5678-90ab-cdef-33333EXAMPLE",
                        "type": "ElasticNetworkInterface",
                        "status": "ATTACHED",
                        "details": [
                            {
                                "name": "subnetId",
                                "value": "subnet-12344321"
                            },
                            {
                                "name": "networkInterfaceId",
                                "value": "eni-12344321"
                            },
                            {
                                "name": "macAddress",
                                "value": "0a:90:09:84:f9:14"
                            },
                            {
                                "name": "privateIPv4Address",
                                "value": "10.0.0.4"
                            }
                        ]
                    }
                ],
                "healthStatus": "UNKNOWN",
                "tags": []
            }
        ],
        "failures": []
    }

For more information, see `Amazon ECS Task Definitions <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html>`_ in the *Amazon ECS Developer Guide*.
