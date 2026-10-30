**To display the details for a user**

The following ``describe-user`` example displays the details for the specified Amazon Connect user. ::

    aws connect describe-user \
        --user-id a1b2c3d4-5678-90ab-cdef-EXAMPLE22222 \
        --instance-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "User": {
            "Id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "Arn": "arn:aws:connect:us-west-2:123456789012:instance/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111/agent/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
            "Username": "Jane",
            "IdentityInfo": {
                "FirstName": "Jane",
                "LastName": "Doe",
                "Email": "example.com"
            },
            "PhoneConfig": {
                "PhoneType": "SOFT_PHONE",
                "AutoAccept": false,
                "AfterContactWorkTimeLimit": 0,
                "DeskPhoneNumber": ""
            },
            "DirectoryUserId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
            "SecurityProfileIds": [
                "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444"
            ],
            "RoutingProfileId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE55555",
            "Tags": {}
        }
    }

For more information, see `Manage Users <https://docs.aws.amazon.com/connect/latest/adminguide/manage-users.html>`__ in the *Amazon Connect Administrator Guide*.
