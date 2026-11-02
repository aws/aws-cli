**To stop a task**

The following ``stop-task`` example stops the specified task from running in the default cluster. ::

    aws ecs stop-task \
        --task 666fdccc2e2d4b6894dd422f4eeee8f8

Output::

    {
        "task": {
            "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/default/666fdccc2e2d4b6894dd422f4eeee8f8",
            "clusterArn": "arn:aws:ecs:us-west-2:123456789012:cluster/default",
            "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/sleep360:3",
            "containerInstanceArn": "arn:aws:ecs:us-west-2:123456789012:container-instance/default/765936fadbdd46b5991a4bd70c2a43d4",
            "overrides": {
                "containerOverrides": []
            },
            "lastStatus": "STOPPED",
            "desiredStatus": "STOPPED",
            "cpu": "128",
            "memory": "128",
            "containers": [],
            "version": 2,
            "stoppedReason": "Taskfailedtostart",
            "stopCode": "TaskFailedToStart",
            "connectivity": "CONNECTED",
            "connectivityAt": 1563421494.186,
            "pullStartedAt": 1563421494.252,
            "pullStoppedAt": 1563421496.252,
            "executionStoppedAt": 1563421497,
            "createdAt": 1563421494.186,
            "stoppingAt": 1563421497.252,
            "stoppedAt": 1563421497.252,
            "group": "family:sleep360",
            "launchType": "EC2",
            "attachments": [],
            "tags": []
        }
    }

For more information, see `Amazon ECS standalone tasks <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/standalone-tasks.html>`__ in the *Amazon ECS Developer Guide*.
