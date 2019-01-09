**To invite users**

This example sends an email invite to invite a user to the specified account.

Command::

  aws chime invite-users --account-id 12a3456b-7c89-012d-3456-78901e23fg45 --user-email-list "user1@example.com" "user2@example.com"

Output::

  {
    "Invites": [
        {
            "InviteId": "a12bc345-6def-78g9-01h2-34jk56789012",
            "Status": "Pending",
            "EmailAddress": "user1@example.com",
            "EmailStatus": "Sent"
        }
        {
            "InviteId": "b12bc345-6def-78g9-01h2-34jk56789012",
            "Status": "Pending",
            "EmailAddress": "user2@example.com",
            "EmailStatus": "Sent"
        }
    ]
  }