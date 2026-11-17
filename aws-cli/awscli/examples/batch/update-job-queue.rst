**To update a job queue**

The following ``update-job-queue`` example disables a job queue so that it can be deleted. ::

    aws batch update-job-queue \
        --job-queue GPGPU \
        --state DISABLED

Output::

    {
        "jobQueueArn": "arn:aws:batch:us-west-2:123456789012:job-queue/GPGPU",
        "jobQueueName": "GPGPU"
    }

For more information, see `Delete a job queue in AWS Batch <https://docs.aws.amazon.com/batch/latest/userguide/delete-job-queue.html>`__ in the *AWS Batch User Guide*.
