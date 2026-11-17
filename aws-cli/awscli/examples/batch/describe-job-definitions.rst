**To describe active job definitions**

The following ``describe-job-definitions`` example describes all of your active job definitions. ::

    aws batch describe-job-definitions \
        --status ACTIVE

Output::

    {
        "jobDefinitions": [
            {
                "status": "ACTIVE",
                "jobDefinitionArn": "arn:aws:batch:us-west-2:123456789012:job-definition/sleep60:1",
                "containerProperties": {
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
                "type": "container",
                "jobDefinitionName": "sleep60",
                "revision": 1
            }
        ]
    }

For more information, see `Job definitions <https://docs.aws.amazon.com/batch/latest/userguide/job_definitions.html>`__ in the *AWS Batch User Guide*.
