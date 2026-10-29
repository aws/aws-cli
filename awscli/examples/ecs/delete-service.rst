**To delete a service**

The following ``delete-service`` example deletes the specified service from a cluster. You can include the ``--force`` parameter to delete a service even if it has not been scaled to zero tasks. ::

    aws ecs delete-service \
        --cluster MyCluster \
        --service MyService1 \
        --force

Output::

    {
        "service": {
            "serviceArn": "arn:aws:ecs:us-west-2:123456789012:service/MyCluster/MyService1",
            "serviceName": "MyService1",
            "clusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/MyCluster",
            "loadBalancers": [],
            "serviceRegistries": [],
            "status": "DRAINING",
            "desiredCount": 0,
            "runningCount": 2,
            "pendingCount": 0,
            "launchType": "EC2",
            "taskDefinition": "arn:aws:ecs:us-west-2:123456789012:task-definition/MyTaskDefinition:1",
            "deploymentConfiguration": {
                "deploymentCircuitBreaker": {
                    "enable": false,
                    "rollback": false
                },
                "maximumPercent": 200,
                "minimumHealthyPercent": 100
            },
            "deployments": [
                {
                    "id": "ecs-svc/1234567890123456789",
                    "status": "PRIMARY",
                    "taskDefinition": "arn:aws:ecs:us-west-2:123456789012:task-definition/MyTaskDefinition:1",
                    "desiredCount": 0,
                    "pendingCount": 0,
                    "runningCount": 2,
                    "failedTasks": 0,
                    "createdAt": "2025-01-15T10:00:00.000000+00:00",
                    "updatedAt": "2025-01-15T11:30:00.000000+00:00",
                    "launchType": "EC2",
                    "rolloutState": "IN_PROGRESS",
                    "rolloutStateReason": "ECS deployment ecs-svc/1234567890123456789 in progress."
                }
            ],
            "events": [],
            "createdAt": "2025-01-15T10:00:00.000000+00:00",
            "placementConstraints": [],
            "placementStrategy": [],
            "schedulingStrategy": "REPLICA",
            "deploymentController": {
                "type": "ECS"
            },
            "createdBy": "arn:aws:iam::123456789012:role/admin",
            "enableECSManagedTags": false,
            "propagateTags": "NONE",
            "enableExecuteCommand": false
        }
    }

For more information, see `Deleting an Amazon ECS service using the console <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/delete-service-v2.html>`__ in the *Amazon ECS Developer Guide*.
