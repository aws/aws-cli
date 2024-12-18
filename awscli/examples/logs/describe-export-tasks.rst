**To List the export tasks**

The following ``describe-export-tasks`` example lists the export tasks. ::

    aws logs describe-export-tasks

Output::

    {
        "exportTasks": [
            {
                "taskId": "a1b2c3d4-5678-90ab-cdef-example11111",
                "taskName": "demo-log-group-1717179675832",
                "logGroupName": "demo-log-group",
                "from": 1716920453000,
                "to": 1717093253000,
                "destination": "S3BucketName",
                "destinationPrefix": "S3BucketPrefix",
                "status": {
                    "code": "COMPLETED",
                    "message": "Completed successfully"
                },
                "executionInfo": {
                    "creationTime": 1717179676323,
                    "completionTime": 1717179677871
                }
            }
        ]
    }

For more information, see `Exporting log data to Amazon S3 <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/S3Export.html>`__ in the *Amazon CloudWatch Logs User Guide*.