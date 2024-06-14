**To describe a task definition**

The following ``describe-task-definition`` example retrieves the details of a task definition. ::

    aws ecs describe-task-definition \
        --task-definition hello_world:8

Output::

    {
        "tasks": [
            {
                "attachments": [
                    {
                        "id": "17f3dff6-a9e9-4d83-99a9-7eb5193c2634",
                        "type": "ElasticNetworkInterface",
                        "status": "ATTACHED",
                        "details": [
                            {
                                "name": "subnetId",
                                "value": "subnet-0d0eab1bb38d5ca64"
                            },
                            {
                                "name": "networkInterfaceId",
                                "value": "eni-0d542ffb4a12aa6d9"
                            },
                            {
                                "name": "macAddress",
                                "value": "0e:6d:18:f6:2d:29"
                            },
                            {
                                "name": "privateDnsName",
                                "value": "ip-10-0-1-170.ec2.internal"
                            },
                            {
                                "name": "privateIPv4Address",
                                "value": "10.0.1.170"
                            }
                        ]
                    }
                ],
                "attributes": [
                    {
                        "name": "ecs.cpu-architecture",
                        "value": "x86_64"
                    }
                ],
                "availabilityZone": "us-east-1b",
                "clusterArn": "arn:aws:ecs:us-east-1:053534965804:cluster/fargate-cluster",
                "connectivity": "CONNECTED",
                "connectivityAt": "2023-11-28T11:10:52.907000-05:00",
                "containers": [
                    {
                        "containerArn": "arn:aws:ecs:us-east-1:053534965804:container/fargate-cluster/c524291ae4154100b601a543108b193a/772c4784-92ae-414e-8df2-03d3358e39fa",
                        "taskArn": "arn:aws:ecs:us-east-1:053534965804:task/fargate-cluster/c524291ae4154100b601a543108b193a",
                        "name": "web",
                        "image": "nginx",
                        "imageDigest": "sha256:10d1f5b58f74683ad34eb29287e07dab1e90f10af243f151bb50aa5dbb4d62ee",
                        "runtimeId": "c524291ae4154100b601a543108b193a-265927825",
                        "lastStatus": "RUNNING",
                        "networkBindings": [],
                        "networkInterfaces": [
                            {
                                "attachmentId": "17f3dff6-a9e9-4d83-99a9-7eb5193c2634",
                                "privateIpv4Address": "10.0.1.170"
                            }
                        ],
                        "healthStatus": "HEALTHY",
                        "cpu": "99",
                        "memory": "100"
                    },
                    {
                        "containerArn": "arn:aws:ecs:us-east-1:053534965804:container/fargate-cluster/c524291ae4154100b601a543108b193a/c051a779-40d2-48ca-ad5e-6ec875ceb610",
                        "taskArn": "arn:aws:ecs:us-east-1:053534965804:task/fargate-cluster/c524291ae4154100b601a543108b193a",
                        "name": "aws-guardduty-agent-FvWGoDU",
                        "imageDigest": "sha256:359b8b014e5076c625daa1056090e522631587a7afa3b2e055edda6bd1141017",
                        "runtimeId": "c524291ae4154100b601a543108b193a-505093495",
                        "lastStatus": "RUNNING",
                        "networkBindings": [],
                        "networkInterfaces": [
                            {
                                "attachmentId": "17f3dff6-a9e9-4d83-99a9-7eb5193c2634",
                                "privateIpv4Address": "10.0.1.170"
                            }
                        ],
                        "healthStatus": "UNKNOWN"
                    }
                ],
                "cpu": "256",
                "createdAt": "2023-11-28T11:10:49.299000-05:00",
                "desiredStatus": "RUNNING",
                "enableExecuteCommand": false,
                "group": "family:webserver",
                "healthStatus": "HEALTHY",
                "lastStatus": "RUNNING",
                "launchType": "FARGATE",
                "memory": "512"
                "platformVersion": "1.4.0",
                "platformFamily": "Linux",
                "pullStartedAt": "2023-11-28T11:10:59.773000-05:00",
                "pullStoppedAt": "2023-11-28T11:11:12.624000-05:00",
                "startedAt": "2023-11-28T11:11:20.316000-05:00",
                "tags": [],
                "taskArn": "arn:aws:ecs:us-east-1:053534965804:task/fargate-cluster/c524291ae4154100b601a543108b193a",
                "taskDefinitionArn": "arn:aws:ecs:us-east-1:053534965804:task-definition/webserver:5",
                "version": 4,
                "ephemeralStorage": {
                    "sizeInGiB": 20
                }
            }
        ],
        "failures": []
    }

For more information, see `Amazon ECS Task Definitions <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html>`_ in the *Amazon ECS Developer Guide*.