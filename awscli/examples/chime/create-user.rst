**To create a user profile for a shared device**

The following ``create-user`` example creates a shared device profile for the specified email address. ::

    aws chime create-user \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --email roomdevice@example.com \
        --user-type SharedDevice

Output::

    {
        "User": {
            "UserId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "AccountId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "PrimaryEmail": "roomdevice@example.com",
            "DisplayName": "Room Device",
            "LicenseType": "Pro",
            "UserType": "SharedDevice",
            "UserRegistrationStatus": "Registered",
            "RegisteredOn": "2020-01-15T22:38:09.806Z",
            "AlexaForBusinessMetadata": {
                "IsAlexaForBusinessEnabled": false
            }
        }
    }

For more information, see `Adding users <https://docs.aws.amazon.com/chime/latest/ag/adding-users.html>`__ in the *Amazon Chime Administration Guide*.
