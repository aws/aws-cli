**To describe an Amazon S3 batch operations job**

The following ``describe-job`` example provides configuration parameters and status for the specified batch operations job. ::

    aws s3control describe-job \
        --account-id 123456789012 \
        --job-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Job": {
            "TerminationDate": "2019-10-03T21:49:53.944Z",
            "JobId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "FailureReasons": [],
            "Manifest": {
                "Spec": {
                    "Fields": [
                        "Bucket",
                        "Key"
                    ],
                    "Format": "S3BatchOperations_CSV_20180820"
                },
                "Location": {
                    "ETag": "69f52a4e9f797e987155d9c8f5880897",
                    "ObjectArn": "arn:aws:s3:::amzn-s3-demo-bucket/inv-report/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222.csv"
                }
            },
            "Operation": {
                "S3PutObjectTagging": {
                    "TagSet": [
                        {
                            "Value": "true",
                            "Key": "confidential"
                        }
                    ]
                }
            },
            "RoleArn": "arn:aws:iam::123456789012:role/S3BatchJobRole",
            "ProgressSummary": {
                "TotalNumberOfTasks": 8,
                "NumberOfTasksFailed": 0,
                "NumberOfTasksSucceeded": 8
            },
            "Priority": 42,
            "Report": {
                "ReportScope": "AllTasks",
                "Format": "Report_CSV_20180820",
                "Enabled": true,
                "Prefix": "batch-op-create-job",
                "Bucket": "arn:aws:s3:::amzn-s3-demo-bucket"
            },
            "JobArn": "arn:aws:s3:us-west-2:123456789012:job/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "CreationTime": "2019-10-03T21:48:48.048Z",
            "Status": "Complete"
        }
    }

For more information, see `Tracking job status and completion reports <https://docs.aws.amazon.com/AmazonS3/latest/userguide/batch-ops-job-status.html>`__ in the *Amazon S3 User Guide*.
