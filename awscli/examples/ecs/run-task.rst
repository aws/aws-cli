**To run a task on your default cluster**

The following ``run-task`` example runs a task on the default cluster and uses a client token. ::

    aws ecs run-task \
        --cluster default \
        --task-definition sleep360:1 \
        --client-token 550e8400-e29b-41d4-a716-446655440000

Output::

    {
        "tasks": [
            {
                "attachments": [],
                "attributes": [
                    {
                        "name": "ecs.cpu-architecture",
                        "value": "x86_64"
                    }
                ],
                "availabilityZone": "us-east-1b",
                "capacityProviderName": "example-capacity-provider",
                "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/default",
                "containerInstanceArn": "arn:aws:ecs:us-east-1:123456789012:container-instance/default/bc4d2ec611d04bb7bb97e83ceEXAMPLE",
                "containers": [
                    {
                        "containerArn": "arn:aws:ecs:us-east-1:123456789012:container/default/d6f51cc5bbc94a47969c92035e9f66f8/75853d2d-711e-458a-8362-0f0aEXAMPLE",
                        "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/default/d6f51cc5bbc94a47969c9203EXAMPLE",
                        "name": "sleep",
                        "image": "busybox",
                        "lastStatus": "PENDING",
                        "networkInterfaces": [],
                        "cpu": "10",
                        "memory": "10"
                    }
                ],
                "cpu": "10",
                "createdAt": "2023-11-21T16:59:34.403000-05:00",
                "desiredStatus": "RUNNING",
                "enableExecuteCommand": false,
                "group": "family:sleep360",
                "lastStatus": "PENDING",
                "launchType": "EC2",
                "memory": "10",
                "overrides": {
                    "containerOverrides": [
                        {
                            "name": "sleep"
                        }
                    ],
                    "inferenceAcceleratorOverrides": []
                },
                "tags": [],
                "taskArn": "arn:aws:ecs:us-east-1:123456789012:task/default/d6f51cc5bbc94a47969c9203EXAMPLE",
                "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/sleep360:1",
                "version": 1
            }
        ],
        "failures": []
    }

For more information, see `Running Tasks <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs_run_task.html>`__ in the *Amazon ECS Developer Guide*.