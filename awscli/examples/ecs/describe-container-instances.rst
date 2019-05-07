**To describe container instance**

The following example shows how to describe a container instance in the ``update`` cluster, using the container instance UUID as an identifier.

Command::

  aws ecs describe-container-instances --cluster update --container-instances 53ac7152-dcd1-4102-81f5-208962864132

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
	                    "integerValue": 3955,
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
	                        "22",
	                        "2376",
	                        "2375",
	                        "51678"
	                    ],
	                    "type": "STRINGSET",
	                    "integerValue": 0
	                }
	            ],
	            "ec2InstanceId": "i-f3c1de3a",
	            "agentConnected": true,
	            "containerInstanceArn": "arn:aws:ecs:us-west-2:123456789012:container-instance/53ac7152-dcd1-4102-81f5-208962864132",
	            "pendingTasksCount": 0,
	            "remainingResources": [
	                {
	                    "integerValue": 2048,
	                    "longValue": 0,
	                    "type": "INTEGER",
	                    "name": "CPU",
	                    "doubleValue": 0.0
	                },
	                {
	                    "integerValue": 3955,
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
	                        "22",
	                        "2376",
	                        "2375",
	                        "51678"
	                    ],
	                    "type": "STRINGSET",
	                    "integerValue": 0
	                }
	            ],
	            "runningTasksCount": 0,
	            "versionInfo": {
	                "agentVersion": "1.0.0",
	                "agentHash": "4023248",
	                "dockerVersion": "DockerVersion: 1.5.0"
	            }
	        }
	    ]
	}