**To create a classification job**

The following ``create-classification-job`` example creates a classification job that analyzes objects in the specified S3 bucket for sensitive data. ::

    aws macie2 create-classification-job \
        --job-type ONE_TIME \
        --name "ExampleClassificationJob" \
        --description "Analyze sensitive data in demo bucket" \
        --s3-job-definition '{
            "bucketDefinitions": [
                {
                    "accountId": "123456789012",
                    "buckets": ["amzn-s3-demo-bucket"]
                }
            ]
        }'

Output::

    {
        "jobArn": "arn:aws:macie2:us-east-1:123456789012:classification-job/42a1c188d7f838f9f0c1234567890",
        "jobId": "42a1c188d7f838f9f0c1234567890"
    }

**To create a scheduled classification job**

The following ``create-classification-job`` example creates a classification job that runs weekly to analyze new objects. ::

    aws macie2 create-classification-job \
        --job-type SCHEDULED \
        --name "WeeklyClassificationJob" \
        --description "Weekly scan for sensitive data" \
        --schedule-frequency '{
            "weeklySchedule": {
                "dayOfWeek": "SUNDAY"
            }
        }' \
        --s3-job-definition '{
            "bucketDefinitions": [
                {
                    "accountId": "123456789012",
                    "buckets": ["amzn-s3-demo-bucket"]
                }
            ]
        }'

Output::

    {
        "jobArn": "arn:aws:macie2:us-east-1:123456789012:classification-job/52b2c299e8g949g0g1d2345678901",
        "jobId": "52b2c299e8g949g0g1d2345678901"
    }
