**Example 1: To change the task definition used in a service**

The following ``update-service`` example updates the ``my-http-service`` service present in ``my-cluster`` cluster to use the ``amazon-ecs-sample`` task definition. ::

    aws ecs update-service --service my-http-service --cluster my-cluster --task-definition amazon-ecs-sample

    {
        "service": {
            "serviceArn": "arn:aws:ecs:us-east-1:123456789012:service/my-cluster/my-http-service",
            "serviceName": "my-http-service",
            "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/my-cluster",
            "loadBalancers": [],
            "serviceRegistries": [],
            "status": "ACTIVE",
            "desiredCount": 0,
            "runningCount": 0,
            "pendingCount": 0,
            "capacityProviderStrategy": [
                {
                    "capacityProvider": "FARGATE",
                    "weight": 1,
                    "base": 0
                }
            ],
            "platformVersion": "LATEST",
            "platformFamily": "Linux",
            "taskDefinition": "arn:aws:ecs:us-east-1:123456789012:task-definition/amazon-ecs-sample:2",
            "deploymentConfiguration": {
                "deploymentCircuitBreaker": {
                    "enable": true,
                    "rollback": true
                },
                "maximumPercent": 200,
                "minimumHealthyPercent": 100,
                "alarms": {
                    "alarmNames": [],
                    "rollback": false,
                    "enable": false
                }
            },
            "deployments": [
                {
                    "id": "ecs-svc/3397730895718564327",
                    "status": "PRIMARY",
                    "taskDefinition": "arn:aws:ecs:us-east-1:123456789012:task-definition/amazon-ecs-sample:2",
                    "desiredCount": 0,
                    "pendingCount": 0,
                    "runningCount": 0,
                    "failedTasks": 0,
                    "createdAt": "2024-11-15T15:44:15.885000+05:30",
                    "updatedAt": "2024-11-15T15:44:15.885000+05:30",
                    "capacityProviderStrategy": [
                        {
                            "capacityProvider": "FARGATE",
                            "weight": 1,
                            "base": 0
                        }
                    ],
                    "platformVersion": "1.4.0",
                    "platformFamily": "Linux",
                    "networkConfiguration": {
                        "awsvpcConfiguration": {
                            "subnets": [
                                "subnet-abcd1234",
                                "subnet-efgh5678",
                                "subnet-ijkl9101",
                                "subnet-mnop1234",
                                "subnet-qrst5678",
                                "subnet-uvmx1234"
                            ],
                            "securityGroups": [
                                "sg-abcd1234"
                            ],
                            "assignPublicIp": "ENABLED"
                        }
                    },
                    "rolloutState": "IN_PROGRESS",
                    "rolloutStateReason": "ECS deployment ecs-svc/3397730895718564327 in progress."
                },
                {
                    "id": "ecs-svc/7461725011061709732",
                    "status": "ACTIVE",
                    "taskDefinition": "arn:aws:ecs:us-east-1:123456789012:task-definition/amazon-ecs-sample:1",
                    "desiredCount": 0,
                    "pendingCount": 0,
                    "runningCount": 0,
                    "failedTasks": 0,
                    "createdAt": "2024-11-15T15:42:08.551000+05:30",
                    "updatedAt": "2024-11-15T15:42:25.758000+05:30",
                    "capacityProviderStrategy": [
                        {
                            "capacityProvider": "FARGATE",
                            "weight": 1,
                            "base": 0
                        }
                    ],
                    "platformVersion": "1.4.0",
                    "platformFamily": "Linux",
                    "networkConfiguration": {
                        "awsvpcConfiguration": {
                            "subnets": [
                                "subnet-abcd1234",
                                "subnet-efgh5678",
                                "subnet-ijkl9101",
                                "subnet-mnop1234",
                                "subnet-qrst5678",
                                "subnet-uvmx1234"
                            ],
                            "securityGroups": [
                                "sg-abcd1234"
                            ],
                            "assignPublicIp": "ENABLED"
                        }
                    },
                    "rolloutState": "COMPLETED",
                    "rolloutStateReason": "ECS deployment ecs-svc/7461725011061709732 completed."
                }
            ],
            "roleArn": "arn:aws:iam::123456789012:role/aws-service-role/ecs.amazonaws.com/AWSServiceRoleForECS",
            "events": [
                {
                    "id": "abcdefgh-7816-4463-8eb9-9f49e488c94d",
                    "createdAt": "2024-11-15T15:42:25.765000+05:30",
                    "message": "(service my-http-service) has reached a steady state."
                },
                {
                    "id": "ijklmnop-0d5a-4b84-95d2-447fefa0079a",
                    "createdAt": "2024-11-15T15:42:25.764000+05:30",
                    "message": "(service my-http-service) (deployment ecs-svc/7461725011061709732) deployment completed."
                }
            ],
            "createdAt": "2024-11-15T15:42:08.551000+05:30",
            "placementConstraints": [],
            "placementStrategy": [],
            "networkConfiguration": {
                "awsvpcConfiguration": {
                    "subnets": [
                        "subnet-abcd1234",
                        "subnet-efgh5678",
                        "subnet-ijkl9101",
                        "subnet-mnop1234",
                        "subnet-qrst5678",
                        "subnet-uvmx1234"
                    ],
                    "securityGroups": [
                        "sg-abcd1234"
                    ],
                    "assignPublicIp": "ENABLED"
                }
            },
            "healthCheckGracePeriodSeconds": 0,
            "schedulingStrategy": "REPLICA",
            "deploymentController": {
                "type": "ECS"
            },
            "createdBy": "arn:aws:iam::123456789012:role/Admin",
            "enableECSManagedTags": true,
            "propagateTags": "NONE",
            "enableExecuteCommand": false
        }
    }

**Example 2: To change the number of tasks in a service**

The following ``update-service`` example updates the desired task count of the service ``my-http-service`` present in ``my-cluster`` cluster to 3. ::

    aws ecs update-service --service my-http-service --cluster my-cluster --desired-count 3

See Example 1 for sample output

For more information, see `Updating a Service <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/update-service.html>`_ in the *Amazon ECS Developer Guide*.
