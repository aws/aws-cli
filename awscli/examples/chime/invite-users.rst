**To invite users to join Amazon Chime**

The following ``invite-users`` example sends an email to invite a user to the specified Amazon Chime account. ::

    aws chime invite-users \
        --account-id a1b2c3d4-5678-90ab-cdef-EXAMPLE11111 \
        --user-email-list "alejandror@example.com" "janed@example.com"

Output::

    {
        "Invites": [
            {
                "InviteId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "Status": "Pending",
                "EmailAddress": "alejandror@example.com",
                "EmailStatus": "Sent"
            },
            {
                "InviteId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "Status": "Pending",
                "EmailAddress": "janed@example.com",
                "EmailStatus": "Sent"
            }
        ]
    }

For more information, see `Managing user permissions and access <https://docs.aws.amazon.com/chime/latest/ag/manage-access.html>`__ in the *Amazon Chime Administration Guide*.
