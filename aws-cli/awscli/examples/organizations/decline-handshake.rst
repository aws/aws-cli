**To decline a handshake sent from another account**

The following ``decline-handshake`` example declines an invitation to join Bill's organization on behalf of Susan, an admin who is the owner of account 222222222222. The DeclineHandshake operation returns a handshake object, showing that the state is now DECLINED. ::

    aws organizations decline-handshake \
        --handshake-id h-examplehandshakeid111

Output::

    {
        "Handshake": {
            "Id": "h-examplehandshakeid111",
            "State": "DECLINED",
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
                    "Value": "susan@example.com"
                },
                {
                    "Type": "NOTES",
                    "Value": "This is an invitation to Susan's account to join the Bill's organization."
                }
            ],
            "Parties": [
                {
                    "Type": "EMAIL",
                    "Id": "susan@example.com"
                },
                {
                    "Type": "ORGANIZATION",
                    "Id": "o-exampleorgid"
                }
            ],
            "Action": "INVITE",
            "RequestedTimestamp": 1470684478.687,
            "ExpirationTimestamp": 1471980478.687,
            "Arn": "arn:aws:organizations::123456789012:handshake/o-exampleorgid/invite/h-examplehandshakeid111"
        }
    }

For more information, see `Accepting or declining account invitations with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_accept-decline-invite.html>`__ in the *AWS Organizations User Guide*.
