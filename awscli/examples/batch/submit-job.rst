**To submit a job**

The following ``submit-job`` example submits a simple container job called `example` to the `HighPriority` job queue. ::

    aws batch submit-job \
        --job-name example \
        --job-queue HighPriority \
        --job-definition sleep60

Output::

    {
        "jobName": "example",
        "jobId": "876da822-4198-45f2-a252-6cea32512ea8"
    }

For more information, see `Tutorial: submit a job <https://docs.aws.amazon.com/batch/latest/userguide/submit_job.html>`__ in the *AWS Batch User Guide*.
