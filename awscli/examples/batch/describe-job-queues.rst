**To describe a job queue**

The following ``describe-job-queues`` example describes the `HighPriority` job queue. ::

    aws batch describe-job-queues \
        --job-queues HighPriority

Output::

    {
        "jobQueues": [
            {
                "status": "VALID",
                "jobQueueArn": "arn:aws:batch:us-west-2:123456789012:job-queue/HighPriority",
                "computeEnvironmentOrder": [
                    {
                        "computeEnvironment": "arn:aws:batch:us-west-2:123456789012:compute-environment/C4OnDemand",
                        "order": 1
                    }
                ],
                "statusReason": "JobQueue Healthy",
                "priority": 1,
                "state": "ENABLED",
                "jobQueueName": "HighPriority"
            }
        ]
    }

For more information, see `Job queues <https://docs.aws.amazon.com/batch/latest/userguide/job_queues.html>`__ in the *AWS Batch User Guide*.
