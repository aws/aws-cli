**To update the primary task set for a service**

The following example shows how to update the primary task set for a service.

Command::

  aws ecs update-service-primary-task-set --cluster MyCluster --service MyService --primary-task-set arn:aws:ecs:us-west-2:123456789012:task-set/MyCluster/MyService/ecs-svc/9223370479726415095

Output::

    {
        "taskSet": {
            "id": "ecs-svc/9223370479726415095",
            "taskSetArn": "arn:aws:ecs:us-west-2:809632081692:task-set/MyCluster/MyService/ecs-svc/9223370479726415095",
            "status": "PRIMARY",
            "taskDefinition": "arn:aws:ecs:us-west-2:809632081692:task-definition/sample-fargate:2",
            "computedDesiredCount": 1,
            "pendingCount": 0,
            "runningCount": 0,
            "createdAt": 1557128360.711,
            "updatedAt": 1557129412.653,
            "launchType": "EC2",
            "networkConfiguration": {
                "awsvpcConfiguration": {
                    "subnets": [
                        "subnet-079ada9e28d4d7130"
                    ],
                    "securityGroups": [
                        "sg-07c919b0ee318e973"
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
    }