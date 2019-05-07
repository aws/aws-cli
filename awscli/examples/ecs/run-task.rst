**To run a task on your default cluster**

The following example shows how to run a task on your default cluster.

Command::

  aws ecs run-task --cluster default --task-definition sleep360:1

Output::

	{
	    "tasks": [
	        {
	            "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/a9f21ea7-c9f5-44b1-b8e6-b31f50ed33c0",
	            "overrides": {
	                "containerOverrides": [
	                    {
	                        "name": "sleep"
	                    }
	                ]
	            },
	            "lastStatus": "PENDING",
	            "containerInstanceArn": "arn:aws:ecs:us-west-2:123456789012:container-instance/ffe3d344-77e2-476c-a4d0-bf560ad50acb",
	            "desiredStatus": "RUNNING",
	            "taskDefinitionArn": "arn:aws:ecs:us-west-2:123456789012:task-definition/sleep360:1",
	            "containers": [
	                {
	                    "containerArn": "arn:aws:ecs:us-west-2:123456789012:container/58591c8e-be29-4ddf-95aa-ee459d4c59fd",
	                    "taskArn": "arn:aws:ecs:us-west-2:123456789012:task/a9f21ea7-c9f5-44b1-b8e6-b31f50ed33c0",
	                    "lastStatus": "PENDING",
	                    "name": "sleep"
	                }
	            ]
	        }
	    ]
	}
