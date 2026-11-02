**To describe a user pool client**

The following ``describe-user-pool-client`` example describes a user pool client. ::

    aws cognito-idp describe-user-pool-client \
        --user-pool-id us-west-2_aaaaaaaaa \
        --client-id 38fjsnc484p94kpqsnet7mpld0

Output::

    {
        "UserPoolClient": {
            "UserPoolId": "us-west-2_aaaaaaaaa",
            "ClientName": "MyApp",
            "ClientId": "38fjsnc484p94kpqsnet7mpld0",
            "ClientSecret": "CLIENT_SECRET",
            "LastModifiedDate": 1548108676.163,
            "CreationDate": 1548108676.163,
            "RefreshTokenValidity": 30,
            "ReadAttributes": [
                "address",
                "birthdate",
                "custom:CustomAttr1",
                "custom:CustomAttr2",
                "email",
                "email_verified",
                "family_name",
                "gender",
                "given_name",
                "locale",
                "middle_name",
                "name",
                "nickname",
                "phone_number",
                "phone_number_verified",
                "picture",
                "preferred_username",
                "profile",
                "updated_at",
                "website",
                "zoneinfo"
            ],
            "WriteAttributes": [
                "address",
                "birthdate",
                "custom:CustomAttr1",
                "custom:CustomAttr2",
                "email",
                "family_name",
                "gender",
                "given_name",
                "locale",
                "middle_name",
                "name",
                "nickname",
                "phone_number",
                "picture",
                "preferred_username",
                "profile",
                "updated_at",
                "website",
                "zoneinfo"
            ],
            "ExplicitAuthFlows": [
                "ADMIN_NO_SRP_AUTH",
                "USER_PASSWORD_AUTH"
            ],
            "AllowedOAuthFlowsUserPoolClient": false
        }
    }

For more information, see `Application-specific settings with app clients <https://docs.aws.amazon.com/cognito/latest/developerguide/user-pool-settings-client-apps.html>`__ in the *Amazon Cognito Developer Guide*.
