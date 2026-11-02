**To get information about a handshake**

The following ``describe-handshake`` example requests details about a handshake. The handshake ID comes either from the original call to ``InviteAccountToOrganization``, or from a call to ``ListHandshakesForAccount`` or ``ListHandshakesForOrganization``. ::

    aws organizations describe-handshake \
        --handshake-id h-examplehandshakeid111

Output::

    {
        "Handshake": {
            "Id": "h-examplehandshakeid111",
            "State": "OPEN",
            "Resources": [
                {
                    "Type": "ORGANIZATION",
                    "Value": "o-exampleorgid",
                    "Resources": [
                        {
                            "Type": "MASTER_EMAIL",
                            "Value": "bill@example.com"
                        },
                        {
                            "Type": "MASTER_NAME",
                            "Value": "Master Account"
                        }
                    ]
                },
                {
                    "Type": "EMAIL",
                    "Value": "anika@example.com"
                }
            ],
            "Parties": [
                {
                    "Type": "ORGANIZATION",
                    "Id": "o-exampleorgid"
                },
                {
                    "Type": "EMAIL",
                    "Id": "anika@example.com"
                }
            ],
            "Action": "INVITE",
            "RequestedTimestamp": 1470158698.046,
            "ExpirationTimestamp": 1471454698.046,
            "Arn": "arn:aws:organizations::123456789012:handshake/o-exampleorgid/invite/h-examplehandshakeid111"
        }
    }

For more information, see `Managing account invitations with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_invites.html>`__ in the *AWS Organizations User Guide*.
