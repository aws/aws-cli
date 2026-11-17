**To list an accounts Amazon S3 batch operations jobs**

The following ``list-jobs`` example lists all recent batch operations jobs for the specified account. ::

    aws s3control list-jobs \
        --account-id 123456789012

Output::

    {
        "Jobs": [
            {
                "Operation": "S3PutObjectTagging",
                "ProgressSummary": {
                    "NumberOfTasksFailed": 0,
                    "NumberOfTasksSucceeded": 8,
                    "TotalNumberOfTasks": 8
                },
                "CreationTime": "2019-10-03T21:48:48.048Z",
                "Status": "Complete",
                "JobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Priority": 42
            },
            {
                "Operation": "S3PutObjectTagging",
                "ProgressSummary": {
                    "NumberOfTasksFailed": 0,
                    "NumberOfTasksSucceeded": 0,
                    "TotalNumberOfTasks": 0
                },
                "CreationTime": "2019-10-03T21:46:07.084Z",
                "Status": "Failed",
                "JobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Priority": 42
            }
        ]
    }

For more information, see `Managing S3 Batch Operations jobs <https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops-managing-jobs.html>`__ in the *Amazon S3 User Guide*.
