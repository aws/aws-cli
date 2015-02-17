**To describe a task**

This example command provides a description of the specified task, using the task UUID as an identifier.

Command::

  aws ecs describe-task --cluster default --task 0cc43cdb-3bee-4407-9c26-c0e6ea5bee84

Output::

	{
	    "failures": [],
	    "tasks": [
	        {
	            "taskArn": "arn:aws:ecs:us-east-1:<aws_account_id>:task/0cc43cdb-3bee-4407-9c26-c0e6ea5bee84",
	            "overrides": {
	                "containerOverrides": [
	                    {
	                        "name": "sleep"
	                    }
	                ]
	            },
	            "lastStatus": "PENDING",
	            "containerInstanceArn": "arn:aws:ecs:us-east-1:<aws_account_id>:container-instance/f6bbb147-5370-4ace-8c73-c7181ded911f",
	            "desiredStatus": "RUNNING",
	            "taskDefinitionArn": "arn:aws:ecs:us-east-1:<aws_account_id>:task-definition/sleep360:1",
	            "containers": [
	                {
	                    "containerArn": "arn:aws:ecs:us-east-1:<aws_account_id>:container/291bb057-f49c-4bd7-9b50-9c891359083b",
	                    "taskArn": "arn:aws:ecs:us-east-1:<aws_account_id>:task/0cc43cdb-3bee-4407-9c26-c0e6ea5bee84",
	                    "lastStatus": "PENDING",
	                    "name": "sleep"
	                }
	            ]
	        }
	    ]
	}
