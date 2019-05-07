**To describe a service**

The following example shows how to describe the ``my-http-service`` service in the default cluster.

Command::

  aws ecs describe-services --services my-http-service

Output::

  {
      "services": [
          {
              "status": "ACTIVE",
              "taskDefinition": "arn:aws:ecs:us-west-2:123456789012:task-definition/amazon-ecs-sample:1",
              "pendingCount": 0,
              "loadBalancers": [],
              "desiredCount": 10,
              "createdAt": 1466801808.595,
              "serviceName": "my-http-service",
              "clusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/default",
              "serviceArn": "arn:aws:ecs:us-west-2:123456789012:service/my-http-service",
              "deployments": [
                  {
                      "status": "PRIMARY",
                      "pendingCount": 0,
                      "createdAt": 1466801808.595,
                      "desiredCount": 10,
                      "taskDefinition": "arn:aws:ecs:us-west-2:123456789012:task-definition/amazon-ecs-sample:1",
                      "updatedAt": 1428326312.703,
                      "id": "ecs-svc/9223370608528463088",
                      "runningCount": 10
                  }
              ],
              "events": [
                  {
                      "message": "(service my-http-service) has reached a steady state.",
                      "id": "97c8a8e0-16a5-4d30-80bd-9e5413f8951b",
                      "createdAt": 1466801812.435
                  }
              ],
              "runningCount": 10
          }
      ],
      "failures": []
  }

**To describe a service**

The following example shows how to describe a service that uses an external deployer.

Command::

  aws ecs describe-services --cluster MyCluster --services MyService

Output::

  {
    "services": [
        {
            "serviceArn": "arn:aws:ecs:us-west-2:123456789012:service/MyCluster/MyService",
            "serviceName": "MyService",
            "clusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/MyCluster",
            "loadBalancers": [],
            "serviceRegistries": [],
            "status": "ACTIVE",
            "desiredCount": 1,
            "runningCount": 0,
            "pendingCount": 0,
            "launchType": "EC2",
            "taskDefinition": "arn:aws:ecs:us-west-2:123456789012:task-definition/sample-fargate:2",
            "deploymentConfiguration": {
                "maximumPercent": 200,
                "minimumHealthyPercent": 100
            },
            "taskSets": [
                {
                    "id": "ecs-svc/9223370479726415095",
                    "taskSetArn": "arn:aws:ecs:us-west-2:123456789012:task-set/MyCluster/MyService/ecs-svc/9223370479726415095",
                    "status": "PRIMARY",
                    "taskDefinition": "arn:aws:ecs:us-west-2:123456789012:task-definition/sample-fargate:2",
                    "computedDesiredCount": 1,
                    "pendingCount": 0,
                    "runningCount": 0,
                    "createdAt": 1557128360.711,
                    "updatedAt": 1557129412.653,
                    "launchType": "EC2",
                    "networkConfiguration": {
                        "awsvpcConfiguration": {
                            "subnets": [
                                "subnet-12344321"
                            ],
                            "securityGroups": [
                                "sg-12344321"
                            ],
                            "assignPublicIp": "DISABLED"
                        }
                    },
                    "loadBalancers": [],
                    "serviceRegistries": [],
                    "scale": {
                        "value": 50.0,
                        "unit": "PERCENT"
                    },
                    "stabilityStatus": "STABILIZING",
                    "stabilityStatusAt": 1557129279.914
                }
            ],
            "deployments": [],
            "roleArn": "arn:aws:iam::123456789012:role/aws-service-role/ecs.amazonaws.com/AWSServiceRoleForECS",
            "events": [
                {
                    "id": "c41d3022-d7c7-413b-bced-b915ea1cd577",
                    "createdAt": 1557129281.988,
                    "message": "(service MyService) updated computedDesiredCount for taskSet ecs-svc/9223370479726415095 to 1."
                },
                {
                    "id": "84baee51-330f-4068-b202-d6d658414bef",
                    "createdAt": 1557128366.872,
                    "message": "(service MyService) has reached a steady state."
                },
                {
                    "id": "8506a2ea-6ee5-469c-aab1-84ef16f2e879",
                    "createdAt": 1557128366.871,
                    "message": "(service MyService, taskSet ecs-svc/9223370479726415095) updated state to STEADY_STATE."
                }
            ],
            "createdAt": 1557128207.101,
            "placementConstraints": [],
            "placementStrategy": [],
            "networkConfiguration": {
                "awsvpcConfiguration": {
                    "subnets": [
                        "subnet-12344321"
                    ],
                    "securityGroups": [
                        "sg-12344321"
                    ],
                    "assignPublicIp": "DISABLED"
                }
            },
            "schedulingStrategy": "REPLICA",
            "deploymentController": {
                "type": "EXTERNAL"
            },
            "enableECSManagedTags": false,
            "propagateTags": "NONE"
        }
    ],
    "failures": []
  }
