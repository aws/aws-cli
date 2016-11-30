**To describe a job**

This example describes a job with the specified job ID.

Command::

  aws batch describe-jobs --jobs bcf0b186-a532-4122-842e-2ccab8d54efb

Output::

	{
	    "jobs": [
	        {
	            "status": "SUBMITTED",
	            "container": {
	                "mountPoints": [],
	                "image": "busybox",
	                "environment": [],
	                "vcpus": 1,
	                "command": [
	                    "sleep",
	                    "60"
	                ],
	                "volumes": [],
	                "memory": 128,
	                "ulimits": []
	            },
	            "parameters": {},
	            "jobDefinition": "sleep60",
	            "jobQueue": "arn:aws:batch:us-east-1:012345678910:job-queue/HighPriority",
	            "jobId": "bcf0b186-a532-4122-842e-2ccab8d54efb",
	            "dependsOn": [],
	            "jobName": "example",
	            "createdAt": 1480483387803
	        }
	    ]
	}
