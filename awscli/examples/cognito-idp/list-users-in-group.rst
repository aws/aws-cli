**To list users in a group**

The following ``list-users-in-group`` example lists users in group MyGroup. ::

    aws cognito-idp list-users-in-group \
        --user-pool-id us-west-2_aaaaaaaaa \
        --group-name MyGroup

Output::

    {
        "Users": [
            {
                "Username": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "Attributes": [
                    {
                        "Name": "sub",
                        "Value": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                    },
                    {
                        "Name": "custom:CustomAttr1",
                        "Value": "New Value!"
                    },
                    {
                        "Name": "email",
                        "Value": "jane@example.com"
                    }
                ],
                "UserCreateDate": 1548102770.284,
                "UserLastModifiedDate": 1548103204.893,
                "Enabled": true,
                "UserStatus": "CONFIRMED"
            },
            {
                "Username": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Attributes": [
                    {
                        "Name": "sub",
                        "Value": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222"
                    },
                    {
                        "Name": "email_verified",
                        "Value": "true"
                    },
                    {
                        "Name": "email",
                        "Value": "diego@example.com"
                    }
                ],
                "UserCreateDate": 1548089817.683,
                "UserLastModifiedDate": 1548089817.683,
                "Enabled": true,
                "UserStatus": "FORCE_CHANGE_PASSWORD"
            }
        ]
    }

For more information, see `Adding groups to a user pool <https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-user-groups.html>`__ in the *Amazon Cognito Developer Guide*.
