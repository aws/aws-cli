**Example 1: To create a group**

The following ``create-group`` example creates a group with a description. ::

    aws cognito-idp create-group \
        --user-pool-id us-west-2_aaaaaaaaa \
        --group-name MyNewGroup \
        --description "New group."

Output::

    {
        "Group": {
            "GroupName": "MyNewGroup",
            "UserPoolId": "us-west-2_aaaaaaaaa",
            "Description": "New group.",
            "LastModifiedDate": 1548270073.795,
            "CreationDate": 1548270073.795
        }
    }

For more information, see `Adding groups to a user pool <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-user-groups.html>`__ in the *Amazon Cognito Developer Guide*.

**Example 2: To create a group with a role and precedence**

The following ``create-group`` example creates a group with a description. It also includes a role and precedence. ::

    aws cognito-idp create-group \
        --user-pool-id us-west-2_aaaaaaaaa \
        --group-name MyNewGroupWithRole \
        --description "New group with a role." \
        --role-arn arn:aws:iam::123456789012:role/MyNewGroupRole \
        --precedence 2

Output::

    {
        "Group": {
            "GroupName": "MyNewGroupWithRole",
            "UserPoolId": "us-west-2_aaaaaaaaa",
            "Description": "New group with a role.",
            "RoleArn": "arn:aws:iam::123456789012:role/MyNewGroupRole",
            "Precedence": 2,
            "LastModifiedDate": 1548270211.761,
            "CreationDate": 1548270211.761
        }
    }

For more information, see `Adding groups to a user pool <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-user-groups.html>`__ in the *Amazon Cognito Developer Guide*.
