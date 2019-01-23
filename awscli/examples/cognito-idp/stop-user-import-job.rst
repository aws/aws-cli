**To stop a user import job**

This example stops a user input job. 

For more information about importing users, see `Importing Users into User Pools From a CSV File`_.

Command::

  aws cognito-idp stop-user-import-job --user-pool-id us-west-1_111111111 --job-id import-TZqNQvDRnW

Output::

  {
    "UserImportJob": {
        "JobName": "import-Test5",
        "JobId": "import-Fx0kARISFL",
        "UserPoolId": "us-west-1_111111111",
        "PreSignedUrl": "PRE_SIGNED_URL",
        "CreationDate": 1548278576.259,
        "StartDate": 1548278623.366,
        "CompletionDate": 1548278626.741,
        "Status": "Stopped",
        "CloudWatchLogsRoleArn": "arn:aws:iam::111111111111:role/CognitoCloudWatchLogsRole",
        "ImportedUsers": 0,
        "SkippedUsers": 0,
        "FailedUsers": 0,
        "CompletionMessage": "The Import Job was stopped by the developer."
    }
  }
  
.. _`Importing Users into User Pools From a CSV File`: https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-using-import-tool.html