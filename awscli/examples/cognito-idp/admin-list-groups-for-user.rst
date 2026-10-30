**To list groups for a user**

The following ``admin-list-groups-for-user`` example lists groups for username diego@example.com. ::

    aws cognito-idp admin-list-groups-for-user --user-pool-id us-west-2_aaaaaaaaa --username diego@example.com

Output::

    {
        "Groups": [
            {
                "Description": "Sample group",
                "Precedence": 1,
                "LastModifiedDate": 1548097827.125,
                "RoleArn": "arn:aws:iam::111111111111:role/SampleRole",
                "GroupName": "SampleGroup",
                "UserPoolId": "us-west-2_aaaaaaaaa",
                "CreationDate": 1548097827.125
            }
        ]
    }