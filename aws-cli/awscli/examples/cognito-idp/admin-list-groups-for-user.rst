**To list groups for a user**

The following ``admin-list-groups-for-user`` example lists groups for username diego@example.com. ::

    aws cognito-idp admin-list-groups-for-user \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username diego@example.com

Output::

    {
        "Groups": [
            {
                "Description": "Sample group",
                "Precedence": 1,
                "LastModifiedDate": 1548097827.125,
                "RoleArn": "arn:aws:iam::123456789012:role/SampleRole",
                "GroupName": "SampleGroup",
                "UserPoolId": "us-west-2_aaaaaaaaa",
                "CreationDate": 1548097827.125
            }
        ]
    }

For more information, see `Adding groups to a user pool <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-user-groups.html>`__ in the *Amazon Cognito Developer Guide*.
