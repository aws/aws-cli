**Example 1: To create a low priority job queue with a single compute environment**

The following ``create-job-queue`` example creates a job queue called `LowPriority` that uses the `M4Spot` compute environment. ::

    aws batch create-job-queue \
        --cli-input-json file://<path_to_json_file>/LowPriority.json

Contents of ``LowPriority.json``::

    {
        "jobQueueName": "LowPriority",
        "state": "ENABLED",
        "priority": 10,
        "computeEnvironmentOrder": [
            {
                "order": 1,
                "computeEnvironment": "M4Spot"
            }
        ]
    }

Output::

    {
        "jobQueueArn": "arn:aws:batch:us-west-2:123456789012:job-queue/LowPriority",
        "jobQueueName": "LowPriority"
    }

For more information, see `Create a job queue <https://docs.aws.amazon.com/batch/latest/userguide/create-job-queue.html>`__ in the *AWS Batch User Guide*.

**Example 2: To create a high priority job queue with two compute environments**

The following ``create-job-queue`` example creates a job queue called `HighPriority` that uses the `C4OnDemand` compute environment with an order of 1 and the `M4Spot` compute environment with an order of 2. The scheduler will attempt to place jobs on the `C4OnDemand` compute environment first. ::

    aws batch create-job-queue \
        --cli-input-json file://<path_to_json_file>/HighPriority.json

Contents of ``HighPriority.json``::

    {
        "jobQueueName": "HighPriority",
        "state": "ENABLED",
        "priority": 1,
        "computeEnvironmentOrder": [
            {
                "order": 1,
                "computeEnvironment": "C4OnDemand"
            },
            {
                "order": 2,
                "computeEnvironment": "M4Spot"
            }
        ]
    }

Output::

    {
        "jobQueueArn": "arn:aws:batch:us-west-2:123456789012:job-queue/HighPriority",
        "jobQueueName": "HighPriority"
    }

For more information, see `Create a job queue <https://docs.aws.amazon.com/batch/latest/userguide/create-job-queue.html>`__ in the *AWS Batch User Guide*.
