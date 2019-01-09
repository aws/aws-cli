**To get a list of users**

This example lists the users for the specified Amazon Chime account.

Command::

  aws chime list-users --account-id 12a3456b-7c89-012d-3456-78901e23fg45

Output::
{
    "Users": [
        {
            "UserId": "1ab2345c-67de-8901-f23g-45h678901j2k",
            "AccountId": "12a3456b-7c89-012d-3456-78901e23fg45",
            "PrimaryEmail": "user1@example.com",
            "DisplayName": "user1 user1",
            "LicenseType": "Pro",
            "UserRegistrationStatus": "Registered",
            "RegisteredOn": "2018-12-20T18:45:25.231Z"
        },
        {
            "UserId": "2ab2345c-67de-8901-f23g-45h678901j2k",
            "AccountId": "12a3456b-7c89-012d-3456-78901e23fg45",
            "PrimaryEmail": "user2@example.com",
            "DisplayName": "user2 user2",
            "LicenseType": "Pro",
            "UserRegistrationStatus": "Registered",
            "RegisteredOn": "2018-12-20T18:45:45.415Z"
        },
        {
            "UserId": "3ab2345c-67de-8901-f23g-45h678901j2k",
            "AccountId": "12a3456b-7c89-012d-3456-78901e23fg45",
            "PrimaryEmail": "user3@example.com",
            "DisplayName": "user3 user3",
            "LicenseType": "Basic",
            "UserRegistrationStatus": "Registered",
            "RegisteredOn": "2018-12-20T18:46:57.747Z"
        },
        {
            "UserId": "4ab2345c-67de-8901-f23g-45h678901j2k",
            "AccountId": "12a3456b-7c89-012d-3456-78901e23fg45",
            "PrimaryEmail": "user4@example.com",
            "DisplayName": "user4 user4",
            "LicenseType": "Basic",
            "UserRegistrationStatus": "Registered",
            "RegisteredOn": "2018-12-20T18:47:15.390Z"
        }
    ]
}