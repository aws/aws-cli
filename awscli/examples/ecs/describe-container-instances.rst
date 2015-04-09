**To describe container instance**

This example command provides a description of the specified container instance in your default region, using the container instance UUID as an identifier.

Command::

  aws ecs describe-container-instance --cluster default --container-instances f2756532-8f13-4d53-87c9-aed50dc94cd7

Output::

	{
	    "failures": [],
	    "containerInstances": [
	        {
	            "status": "ACTIVE",
	            "registeredResources": [
	                {
	                    "integerValue": 2048,
	                    "longValue": 0,
	                    "type": "INTEGER",
	                    "name": "CPU",
	                    "doubleValue": 0.0
	                },
	                {
	                    "integerValue": 3768,
	                    "longValue": 0,
	                    "type": "INTEGER",
	                    "name": "MEMORY",
	                    "doubleValue": 0.0
	                },
	                {
	                    "name": "PORTS",
	                    "longValue": 0,
	                    "doubleValue": 0.0,
	                    "stringSetValue": [
	                        "2376",
	                        "22",
	                        "51678",
	                        "2375"
	                    ],
	                    "type": "STRINGSET",
	                    "integerValue": 0
	                }
	            ],
	            "ec2InstanceId": "i-807f3249",
	            "agentConnected": true,
	            "containerInstanceArn": "arn:aws:ecs:<region>:<aws_account_id>:container-instance/f2756532-8f13-4d53-87c9-aed50dc94cd7",
	            "pendingTasksCount": 0,
	            "remainingResources": [
	                {
	                    "integerValue": 1948,
	                    "longValue": 0,
	                    "type": "INTEGER",
	                    "name": "CPU",
	                    "doubleValue": 0.0
	                },
	                {
	                    "integerValue": 3668,
	                    "longValue": 0,
	                    "type": "INTEGER",
	                    "name": "MEMORY",
	                    "doubleValue": 0.0
	                },
	                {
	                    "name": "PORTS",
	                    "longValue": 0,
	                    "doubleValue": 0.0,
	                    "stringSetValue": [
	                        "2376",
	                        "22",
	                        "80",
	                        "51678",
	                        "2375"
	                    ],
	                    "type": "STRINGSET",
	                    "integerValue": 0
	                }
	            ],
	            "runningTasksCount": 1
	        }
	    ]
	}