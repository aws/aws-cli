**To get a user**

The following ``admin-get-user`` example gets information about username jane@example.com. ::

    aws cognito-idp admin-get-user \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username jane@example.com

Output::

    {
        "Username": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "Enabled": true,
        "UserStatus": "FORCE_CHANGE_PASSWORD",
        "UserCreateDate": 1548108509.537,
        "UserAttributes": [
            {
                "Name": "sub",
                "Value": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
            },
            {
                "Name": "email_verified",
                "Value": "true"
            },
            {
                "Name": "phone_number_verified",
                "Value": "true"
            },
            {
                "Name": "phone_number",
                "Value": "+01115551212"
            },
            {
                "Name": "email",
                "Value": "jane@example.com"
            }
        ],
        "UserLastModifiedDate": 1548108509.537
    }

For more information, see `Managing and searching for user accounts <https://docs.aws.amazon.com/cognito/latest/developerguide/how-to-manage-user-accounts.html>`__ in the *Amazon Cognito Developer Guide*.
