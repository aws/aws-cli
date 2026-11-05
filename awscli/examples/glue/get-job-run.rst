**To get information about a job run**

The following ``get-job-run`` example retrieves information about a job run. ::

    aws glue get-job-run \
        --job-name "Combine legistators data" \
        --run-id jr_012e1765065050a4d94d761755e5c62538ee1aad6f17d39f527e9140cf0c9a5e  

Output::

    {
        "JobRun": {
            "Id": "jr_012e1765065050a4d94d761755e5c62538ee1aad6f17d39f527e9140cf0c9a5e",
            "Attempt": 0,
            "JobName": "Combine legistators data",
            "StartedOn": 1602873931.255,
            "LastModifiedOn": 1602874075.985,
            "CompletedOn": 1602874075.985,
            "JobRunState": "SUCCEEDED",
            "Arguments": {
                "--enable-continuous-cloudwatch-log": "true",
                "--enable-metrics": "",
                "--enable-spark-ui": "true",
                "--job-bookmark-option": "job-bookmark-enable",
                "--spark-event-logs-path": "s3://amzn-s3-demo-bucket/sparkHistoryLogs/"
            },
            "PredecessorRuns": [],
            "AllocatedCapacity": 10,
            "ExecutionTime": 117,
            "Timeout": 2880,
            "MaxCapacity": 10.0,
            "WorkerType": "G.1X",
            "NumberOfWorkers": 10,
            "LogGroupName": "/aws-glue/jobs",
            "GlueVersion": "2.0"
        }
    }

For more information, see `Job Runs <https://docs.aws.amazon.com/glue/latest/dg/aws-glue-api-jobs-runs.html>`__ in the *AWS Glue Developer Guide*.
