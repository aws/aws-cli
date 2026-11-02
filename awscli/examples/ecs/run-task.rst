**Example 1: To run a task on your default cluster**

The following ``run-task`` example runs a task on the default cluster and uses a client token. ::

    aws ecs run-task \
        --cluster default \
        --task-definition sleep360:1 \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

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
                "availabilityZone": "us-west-2b",
                "capacityProviderName": "example-capacity-provider",
                "clusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/default",
                "containerInstanceArn": "arn:aws:ecs:us-west-2:123456789012:container-instance/default/bc4d2ec611d04bb7bb97e83ceEXAMPLE",
                "containers": [
                    {
                        "containerArn": "arn:aws:ecs:us-west-2:123456789012:container/default/d6f51cc5bbc94a47969c92035e9f66f8/75853d2d-711e-458a-8362-0f0aEXAMPLE",
                        "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/default/d6f51cc5bbc94a47969c9203EXAMPLE",
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
                "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/default/d6f51cc5bbc94a47969c9203EXAMPLE",
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/sleep360:1",
                "version": 1
            }
        ],
        "failures": []
    }

For more information, see `Running an application as a standalone task <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/standalone-task-create.html>`__ in the *Amazon ECS Developer Guide*.

**Example 2: To configure an Amazon EBS volume for a standalone task**

The following ``run-task`` example configures an encrypted Amazon EBS volume for a Fargate task on the default cluster. You must have an Amazon ECS infrastructure role configured with the ``AmazonECSInfrastructureRolePolicyForVolumes`` managed policy attached. You must specify a task definition with the same volume name as in the ``run-task`` request. This example uses the ``--cli-input-json`` option and a JSON input file called ``ebs.json``. ::

    aws ecs run-task \
        --cli-input-json file://ebs.json

Contents of ``ebs.json``::

    {
        "cluster": "default",
        "taskDefinition": "mytaskdef",
        "launchType": "FARGATE",
        "networkConfiguration":{
            "awsvpcConfiguration":{
                "assignPublicIp": "ENABLED",
                "securityGroups": ["sg-12344321"],
                "subnets":["subnet-12344321"]
            }
        },
        "volumeConfigurations": [
            {
                "name": "myEBSVolume",
                "managedEBSVolume": {
                    "volumeType": "gp3",
                    "sizeInGiB": 100,
                    "roleArn":"arn:aws:iam::1111222333:role/ecsInfrastructureRole",
                    "encrypted": true,
                    "kmsKeyId": "arn:aws:kms:region:123456789012:key/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
                }
            }
        ]
    }

Output::

    {
        "tasks": [
            {
                "attachments": [
                    {
                        "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                        "type": "ElasticNetworkInterface",
                        "status": "PRECREATED",
                        "details": [
                            {
                                "name": "subnetId",
                                "value": "subnet-12344321"
                            }
                        ]
                    },
                    {
                        "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                        "type": "AmazonElasticBlockStorage",
                        "status": "CREATED",
                        "details": [
                            {
                                "name": "roleArn",
                                "value": "arn:aws:iam::123456789012:role/ecsInfrastructureRole"
                            },
                            {
                                "name": "volumeName",
                                "value": "myEBSVolume"
                            },
                            {
                                "name": "deleteOnTermination",
                                "value": "true"
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
                "availabilityZone": "us-west-2b",
                "clusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/default",
                "containers": [
                    {
                        "containerArn": "arn:aws:ecs:us-west-2:123456789012:container/default/7f1fbd3629434cc4b82d72d2f09b67c9/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                        "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/default/7f1fbd3629434cc4b82d72d2f09b67c9",
                        "name": "container-using-ebs",
                        "image": "amazonlinux:2",
                        "lastStatus": "PENDING",
                        "networkInterfaces": [],
                        "cpu": "0"
                    }
                ],
                "cpu": "1024",
                "createdAt": "2025-01-23T10:29:46.650000-06:00",
                "desiredStatus": "RUNNING",
                "enableExecuteCommand": false,
                "group": "family:mytaskdef",
                "lastStatus": "PROVISIONING",
                "launchType": "FARGATE",
                "memory": "3072",
                "overrides": {
                    "containerOverrides": [
                        {
                            "name": "container-using-ebs"
                        }
                    ],
                    "inferenceAcceleratorOverrides": []
                },
                "platformVersion": "1.4.0",
                "platformFamily": "Linux",
                "tags": [],
                "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/default/7f1fbd3629434cc4b82d72d2f09b67c9",
                "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/mytaskdef:4",
                "version": 1,
                "ephemeralStorage": {
                    "sizeInGiB": 20
                },
                "fargateEphemeralStorage": {
                    "sizeInGiB": 20
                }
            }
        ],
        "failures": []
    }

For more information, see `Use Amazon EBS volumes with Amazon ECS <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ebs-volumes.html>`__ in the *Amazon ECS Developer Guide*.
