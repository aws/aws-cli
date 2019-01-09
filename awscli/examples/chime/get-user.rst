**To get user details**

This example lists details for the specified user.

Command::

  aws chime get-user --account-id 12a3456b-7c89-012d-3456-78901e23fg45 --user-id 1ab2345c-67de-8901-f23g-45h678901j2k

Output::
{
    "User": {
        "UserId": "1ab2345c-67de-8901-f23g-45h678901j2k",
        "AccountId": "12a3456b-7c89-012d-3456-78901e23fg45",
        "PrimaryEmail": "user1@example.com",
        "DisplayName": "user1 user1",
        "LicenseType": "Pro",
        "UserRegistrationStatus": "Registered",
        "RegisteredOn": "2018-12-20T18:45:25.231Z",
        "PersonalPIN": "XXXXXXXXXX"
    }
}