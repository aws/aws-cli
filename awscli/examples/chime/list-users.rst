**To list the users in an account**

The following ``list-users`` example lists the users for the specified Amazon Chime account. ::

    aws chime list-users \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Users": [
            {
                "UserId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "PrimaryEmail": "mariag@example.com",
                "DisplayName": "Maria Garcia",
                "LicenseType": "Pro",
                "UserType": "PrivateUser",
                "UserRegistrationStatus": "Registered",
                "RegisteredOn": "2018-12-20T18:45:25.231Z",
                "AlexaForBusinessMetadata": {
                    "IsAlexaForBusinessEnabled": false
                }
            },
            {
                "UserId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "PrimaryEmail": "richardr@example.com",
                "DisplayName": "Richard Roe",
                "LicenseType": "Pro",
                "UserType": "PrivateUser",
                "UserRegistrationStatus": "Registered",
                "RegisteredOn": "2018-12-20T18:45:45.415Z",
                "AlexaForBusinessMetadata": {
                    "IsAlexaForBusinessEnabled": false
                }
            },
            {
                "UserId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "PrimaryEmail": "saanvis@example.com",
                "DisplayName": "Saanvi Sarkar",
                "LicenseType": "Basic",
                "UserType": "PrivateUser",
                "UserRegistrationStatus": "Registered",
                "RegisteredOn": "2018-12-20T18:46:57.747Z",
                "AlexaForBusinessMetadata": {
                    "IsAlexaForBusinessEnabled": false
                }
            },
            {
                "UserId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
                "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "PrimaryEmail": "wxiulan@example.com",
                "DisplayName": "Wang Xiulan",
                "LicenseType": "Basic",
                "UserType": "PrivateUser",
                "UserRegistrationStatus": "Registered",
                "RegisteredOn": "2018-12-20T18:47:15.390Z",
                "AlexaForBusinessMetadata": {
                    "IsAlexaForBusinessEnabled": false
                }
            }
        ]
    }

For more information, see `Managing users <https://docs.aws.amazon.com/chime/latest/ag/manage-users.html>`__ in the *Amazon Chime Administration Guide*.
