**Example 1: To list running jobs**

The following ``list-jobs`` example lists the running jobs in the `HighPriority` job queue. ::

    aws batch list-jobs --job-queue HighPriority

Output::

    {
        "jobSummaryList": [
            {
                "jobName": "example",
                "jobId": "e66ff5fd-a1ff-4640-b1a2-0b0a142f49bb"
            }
        ]
    }


**Example 2: To list submitted jobs**

The following ``list-jobs`` example lists jobs in the `HighPriority` job queue that are in the `SUBMITTED` job status. ::

    aws batch list-jobs --job-queue HighPriority --job-status SUBMITTED

Output::

    {
        "jobSummaryList": [
            {
                "jobName": "example",
                "jobId": "68f0c163-fbd4-44e6-9fd1-25b14a434786"
            }
        ]
    }
