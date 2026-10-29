**To create a user import job**

The following ``create-user-import-job`` example creates a user import job named MyImportJob. ::

    aws cognito-idp create-user-import-job \
        --user-pool-id us-west-2_aaaaaaaaa \
        --job-name MyImportJob \
        --cloud-watch-logs-role-arn arn:aws:iam::123456789012:role/CognitoCloudWatchLogsRole

Output::

    {
        "UserImportJob": {
            "JobName": "MyImportJob",
            "JobId": "import-qQ0DCt2fRh",
            "UserPoolId": "us-west-2_aaaaaaaaa",
            "PreSignedUrl": "PRE_SIGNED_URL",
            "CreationDate": 1548271795.471,
            "Status": "Created",
            "CloudWatchLogsRoleArn": "arn:aws:iam::123456789012:role/CognitoCloudWatchLogsRole",
            "ImportedUsers": 0,
            "SkippedUsers": 0,
            "FailedUsers": 0
        }
    }

Upload the .csv file with curl using the pre-signed URL. ::

    curl -v -T "PATH_TO_CSV_FILE" -H "x-amz-server-side-encryption:aws:kms" "PRE_SIGNED_URL"

For more information, see `Importing users into user pools from a CSV file <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-using-import-tool.html>`__ in the *Amazon Cognito Developer Guide*.