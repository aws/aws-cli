**To describe a task**

The following example shows how to describe a task. The task can be specified by either the ID or full ARN of the task.

Command::

  aws ecs describe-tasks --cluster MyCluster --tasks arn:aws:ecs:us-west-2:123456789012:task/MyCluster/c37ec22853be413da016fefeaa202bd8

Output::

	{
    "tasks": [
        {
            "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/MyCluster/c37ec22853be413da016fefeaa202bd8",
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
                    "containerArn": "arn:aws:ecs:us-west-2:123456789012:container/7a7cb7e5-4fb1-40c7-8aa8-614aefe6a272",
                    "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/MyCluster/c37ec22853be413da016fefeaa202bd8",
                    "name": "fargate-app",
                    "lastStatus": "RUNNING",
                    "networkBindings": [],
                    "networkInterfaces": [
                        {
                            "attachmentId": "773670f6-9a57-4d04-ad2e-4617d9620f38",
                            "privateIpv4Address": "10.0.0.4"
                        }
                    ],
                    "healthStatus": "UNKNOWN",
                    "cpu": "0"
                }
            ],
            "startedBy": "ecs-svc/9223370479720765889",
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
                    "id": "773670f6-9a57-4d04-ad2e-4617d9620f38",
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