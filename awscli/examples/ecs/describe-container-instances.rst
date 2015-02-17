**To describe container instance**

This example command provides a description of the specified container instance in your default region, using the container instance UUID as an identifier.

Command::

  aws ecs describe-container-instance --cluster default --container-instance f6bbb147-5370-4ace-8c73-c7181ded911f

Output::

	{
	    "failures": [],
	    "containerInstances": [
	        {
	            "status": "ACTIVE",
	            "remainingResources": [
	                {
	                    "integerValue": 32748,
	                    "longValue": 0,
	                    "type": "INTEGER",
	                    "name": "CPU",
	                    "doubleValue": 0.0
	                },
	                {
	                    "integerValue": 60377,
	                    "longValue": 0,
	                    "type": "INTEGER",
	                    "name": "MEMORY",
	                    "doubleValue": 0.0
	                }
	            ],
	            "registeredResources": [
	                {
	                    "integerValue": 32768,
	                    "longValue": 0,
	                    "type": "INTEGER",
	                    "name": "CPU",
	                    "doubleValue": 0.0
	                },
	                {
	                    "integerValue": 60397,
	                    "longValue": 0,
	                    "type": "INTEGER",
	                    "name": "MEMORY",
	                    "doubleValue": 0.0
	                }
	            ],
	            "containerInstanceArn": "arn:aws:ecs:us-east-1:<aws_account_id>:container-instance/f6bbb147-5370-4ace-8c73-c7181ded911f",
	            "ec2InstanceId": "i-0f51df05"
	        }
	    ]
	}
