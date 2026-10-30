**To update a group**

The following ``update-group`` example updates the description and precedence for MyGroup. ::

    aws cognito-idp update-group \
        --user-pool-id us-west-2_aaaaaaaaa \
        --group-name MyGroup \
        --description "New description" \
        --precedence 2

Output::

    {
        "Group": {
            "GroupName": "MyGroup",
            "UserPoolId": "us-west-2_aaaaaaaaa",
            "Description": "New description",
            "RoleArn": "arn:aws:iam::123456789012:role/MyRole",
            "Precedence": 2,
            "LastModifiedDate": 1548800862.812,
            "CreationDate": 1548097827.125
        }
    }

For more information, see `Adding groups to a user pool <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-user-groups.html>`__ in the *Amazon Cognito Developer Guide*.
