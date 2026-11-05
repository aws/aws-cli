**To create a user**

The following ``admin-create-user`` example creates a user with the specified settings email address and phone number. ::

    aws cognito-idp admin-create-user \
        --user-pool-id us-west-2_aaaaaaaaa \
        --username diego \
        --user-attributes Name=email,Value=diego@example.com Name=phone_number,Value="+15555551212" \
        --message-action SUPPRESS

Output::

    {
        "User": {
            "Username": "diego",
            "Attributes": [
                {
                    "Name": "sub",
                    "Value": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
                },
                {
                    "Name": "phone_number",
                    "Value": "+15555551212"
                },
                {
                    "Name": "email",
                    "Value": "diego@example.com"
                }
            ],
            "UserCreateDate": 1548099495.428,
            "UserLastModifiedDate": 1548099495.428,
            "Enabled": true,
            "UserStatus": "FORCE_CHANGE_PASSWORD"
        }
    }

For more information, see `Creating user accounts as administrator <https://docs.aws.amazon.com/cognito/latest/developerguide/how-to-create-user-accounts.html>`__ in the *Amazon Cognito Developer Guide*.
