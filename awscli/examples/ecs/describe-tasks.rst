**To describe a task**

This example command provides a description of the specified task, using the task UUID as an identifier.

Command::

  aws ecs describe-tasks --tasks 68ef0f55-2ac3-420a-962f-a64d587fd38d

Output::

	{
	    "failures": [],
	    "tasks": [
	        {
	            "taskArn": "arn:aws:ecs:us-east-1:<aws_account_id>:task/68ef0f55-2ac3-420a-962f-a64d587fd38d",
	            "overrides": {
	                "containerOverrides": [
	                    {
	                        "name": "timer"
	                    },
	                    {
	                        "name": "web"
	                    }
	                ]
	            },
	            "lastStatus": "RUNNING",
	            "containerInstanceArn": "arn:aws:ecs:us-east-1:<aws_account_id>:container-instance/22878e8e-25f1-4868-8bee-6a36a8bee7c1",
	            "desiredStatus": "RUNNING",
	            "taskDefinitionArn": "arn:aws:ecs:us-east-1:<aws_account_id>:task-definition/web-timer:2",
	            "containers": [
	                {
	                    "containerArn": "arn:aws:ecs:us-east-1:<aws_account_id>:container/87539a7c-5769-4860-863c-e0d48da8a855",
	                    "taskArn": "arn:aws:ecs:us-east-1:<aws_account_id>:task/68ef0f55-2ac3-420a-962f-a64d587fd38d",
	                    "lastStatus": "RUNNING",
	                    "name": "timer",
	                    "networkBindings": []
	                },
	                {
	                    "containerArn": "arn:aws:ecs:us-east-1:<aws_account_id>:container/8e899803-b471-4d74-a9d9-3081c76b23fd",
	                    "taskArn": "arn:aws:ecs:us-east-1:<aws_account_id>:task/68ef0f55-2ac3-420a-962f-a64d587fd38d",
	                    "lastStatus": "RUNNING",
	                    "name": "web",
	                    "networkBindings": [
	                        {
	                            "bindIP": "0.0.0.0",
	                            "containerPort": 80,
	                            "hostPort": 80
	                        }
	                    ]
	                }
	            ]
	        }
	    ]
	}
