**Example 1: To list running jobs**

The following ``list-jobs`` example lists the running jobs in the `HighPriority` job queue. ::

    aws batch list-jobs \
        --job-queue HighPriority

Output::

    {
        "jobSummaryList": [
            {
                "jobName": "example",
                "jobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            }
        ]
    }

For more information, see `Job states <https://docs.aws.amazon.com/batch/latest/userguide/job_states.html>`__ in the *AWS Batch User Guide*.

**Example 2: To list submitted jobs**

The following ``list-jobs`` example lists jobs in the `HighPriority` job queue that are in the `SUBMITTED` job status. ::

    aws batch list-jobs \
        --job-queue HighPriority \
        --job-status SUBMITTED

Output::

    {
        "jobSummaryList": [
            {
                "jobName": "example",
                "jobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
            }
        ]
    }

For more information, see `Job states <https://docs.aws.amazon.com/batch/latest/userguide/job_states.html>`__ in the *AWS Batch User Guide*.
