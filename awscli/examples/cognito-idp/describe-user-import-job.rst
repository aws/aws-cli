**To describe a user import job**

The following ``describe-user-import-job`` example describes a user import job. ::

    aws cognito-idp describe-user-import-job \
        --user-pool-id us-west-2_aaaaaaaaa \
        --job-id import-TZqNQvDRnW

Output::

    {
        "UserImportJob": {
            "JobName": "import-Test1",
            "JobId": "import-TZqNQvDRnW",
            "UserPoolId": "us-west-2_aaaaaaaaa",
            "PreSignedUrl": "PRE_SIGNED URL",
            "CreationDate": 1548271708.512,
            "Status": "Created",
            "CloudWatchLogsRoleArn": "arn:aws:iam::123456789012:role/CognitoCloudWatchLogsRole",
            "ImportedUsers": 0,
            "SkippedUsers": 0,
            "FailedUsers": 0
        }
    }

For more information, see `Importing users into user pools from a CSV file <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-using-import-tool.html>`__ in the *Amazon Cognito Developer Guide*.