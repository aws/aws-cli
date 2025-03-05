**Example 1: To change the number of instantiations in a service**

The following ``update-service`` example updates the desired task count of the service ``my-http-service`` to 2. ::

    aws ecs update-service \
       --cluster MyCluster
       --service my-http-service \
       --desired-count 2

Output::

    {
        "service": {
            "serviceArn": "arn:aws:ecs:us-east-1:123456789012:service/MyCluster/my-http-service",
            "serviceName": "my-http-service",
            "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/MyCluster",
            "loadBalancers": [],
            "serviceRegistries": [],
            "status": "ACTIVE",
            "desiredCount": 2,
            "runningCount": 1,
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
            "taskDefinition": "arn:aws:ecs:us-east-1:123456789012:task-definition/MyTaskDefinition",
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
                    "id": "ecs-svc/1976744184940610707",
                    "status": "PRIMARY",
                    "taskkDefinition": "arn:aws:ecs:us-east-1:123456789012:task-definition/MyTaskDefinition",
                    "desiredCount": 1,
                    "pendingCount": 0,
                    "runningCount": 1,
                    "failedTasks": 0,
                    "createdAt": "2024-12-03T16:24:25.225000-05:00",
                    "updatedAt": "2024-12-03T16:25:15.837000-05:00",
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
                                "subnet-0d0eab1bb38d5ca64",
                                "subnet-0db5010045995c2d5"
                            ],
                            "securityGroups": [
                                "sg-02556bf85a191f59a"
                            ],
                            "assignPublicIp": "ENABLED"
                        }
                    },
                    "rolloutState": "COMPLETED",
                    "rolloutStateReason": "ECS deployment ecs-svc/1976744184940610707 completed."
                }
            ],
            "roleArn": "arn:aws:iam::123456789012:role/aws-service-role/ecs.amazonaws.com/AWSServiceRoleForECS",
            "events": [
                {
                    "id": "f27350b9-4b2a-4e2e-b72e-a4b68380de45",
                    "createdAt": "2024-12-30T13:24:07.345000-05:00",
                    "message": "(service my-http-service) has reached a steady state."
                },
                {
                    "id": "e764ec63-f53f-45e3-9af2-d99f922d2957",
                    "createdAt": "2024-12-30T12:32:21.600000-05:00",
                    "message": "(service my-http-service) has reached a steady state."
                },          
                {
                    "id": "28444756-c2fa-47f8-bd60-93a8e05f3991",
                    "createdAt": "2024-12-08T19:26:10.367000-05:00",
                    "message": "(service my-http-service) has reached a steady state."
                }
            ],
            "createdAt": "2024-12-03T16:24:25.225000-05:00",
            "placementConstraints": [],
            "placementStrategy": [],
            "networkConfiguration": {
                "awsvpcConfiguration": {
                    "subnets": [
                        "subnet-0d0eab1bb38d5ca64",
                        "subnet-0db5010045995c2d5"
                    ],
                    "securityGroups": [
                        "sg-02556bf85a191f59a"
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
            "enableExecuteCommand": false,
            "availabilityZoneRebalancing": "ENABLED"
        }
    }

For more information, see `Updating an Amazon ECS service using the console <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/update-service-console-v2.html>`__ in the *Amazon ECS Developer Guide*.

**Example 2: To turn on Availability Zone rebalancing for a service**

The following ``update-service`` example turns on Availability Zone rebalancing for the service ``my-http-service``. ::

    aws ecs update-service \
        --cluster MyCluster \
        --service my-http-service \
        --availability-zone-rebalancing ENABLED

Output::

    {
        "service": {
            "serviceArn": "arn:aws:ecs:us-east-1:123456789012:service/MyCluster/my-http-service",
            "serviceName": "my-http-service",
            "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/MyCluster",
            "loadBalancers": [],
            "serviceRegistries": [],
            "status": "ACTIVE",
            "desiredCount": 2,
            "runningCount": 1,
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
            "taskDefinition": "arn:aws:ecs:us-east-1:123456789012:task-definition/MyTaskDefinition",
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
                    "id": "ecs-svc/1976744184940610707",
                    "status": "PRIMARY",
                    "taskkDefinition": "arn:aws:ecs:us-east-1:123456789012:task-definition/MyTaskDefinition",
                    "desiredCount": 1,
                    "pendingCount": 0,
                    "runningCount": 1,
                    "failedTasks": 0,
                    "createdAt": "2024-12-03T16:24:25.225000-05:00",
                    "updatedAt": "2024-12-03T16:25:15.837000-05:00",
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
                                "subnet-0d0eab1bb38d5ca64",
                                "subnet-0db5010045995c2d5"
                            ],
                            "securityGroups": [
                                "sg-02556bf85a191f59a"
                            ],
                            "assignPublicIp": "ENABLED"
                        }
                    },
                    "rolloutState": "COMPLETED",
                    "rolloutStateReason": "ECS deployment ecs-svc/1976744184940610707 completed."
                }
            ],
            "roleArn": "arn:aws:iam::123456789012:role/aws-service-role/ecs.amazonaws.com/AWSServiceRoleForECS",
            "events": [],
            "createdAt": "2024-12-03T16:24:25.225000-05:00",
            "placementConstraints": [],
            "placementStrategy": [],
            "networkConfiguration": {
                "awsvpcConfiguration": {
                    "subnets": [
                        "subnet-0d0eab1bb38d5ca64",
                        "subnet-0db5010045995c2d5"
                    ],
                    "securityGroups": [
                        "sg-02556bf85a191f59a"
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
            "enableExecuteCommand": false,
            "availabilityZoneRebalancing": "ENABLED"
        }
    }

For more information, see `Updating an Amazon ECS service using the console <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/update-service-console-v2.html>`__ in the *Amazon ECS Developer Guide*.