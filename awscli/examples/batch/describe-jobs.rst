**To describe a job**

The following ``describe-jobs`` example describes a job with the specified job ID. ::

    aws batch describe-jobs \
        --jobs a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

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
                "jobDefinition": "arn:aws:batch:us-west-2:123456789012:job-definition/sleep60:1",
                "jobQueue": "arn:aws:batch:us-west-2:123456789012:job-queue/HighPriority",
                "jobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "dependsOn": [],
                "jobName": "example",
                "createdAt": 1480483387803
            }
        ]
    }

For more information, see `Jobs <https://docs.aws.amazon.com/batch/latest/userguide/jobs.html>`__ in the *AWS Batch User Guide*.
