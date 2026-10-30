**To create a csv header**

The following ``get-csv-header`` example gets the CSV header for a user pool. ::

    aws cognito-idp get-csv-header --user-pool-id us-west-2_aaaaaaaaa

Output::

    {
        "UserPoolId": "us-west-2_aaaaaaaaa",
        "CSVHeader": [
            "name",
            "given_name",
            "family_name",
            "middle_name",
            "nickname",
            "preferred_username",
            "profile",
            "picture",
            "website",
            "email",
            "email_verified",
            "gender",
            "birthdate",
            "zoneinfo",
            "locale",
            "phone_number",
            "phone_number_verified",
            "address",
            "updated_at",
            "cognito:mfa_enabled",
            "cognito:username"
        ]
    }

For more information about importing users, see `Importing Users into User Pools From a CSV File`_.

.. _`Importing Users into User Pools From a CSV File`: https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-using-import-tool.html