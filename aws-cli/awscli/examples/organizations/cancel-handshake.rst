**To cancel a handshake sent from another account**

The following ``cancel-handshake`` example cancels a handshake that Bill previously sent to invite Susan's account to join his organization. He changes his mind and decides to cancel the invitation before Susan accepts it. The output shows that the handshake state is now ``CANCELED``. ::

    aws organizations cancel-handshake \
        --handshake-id h-examplehandshakeid111

Output::

    {
        "Handshake": {
            "Id": "h-examplehandshakeid111",
            "State":"CANCELED",
            "Action": "INVITE",
            "Arn": "arn:aws:organizations::123456789012:handshake/o-exampleorgid/invite/h-examplehandshakeid111",
            "Parties": [
                {
                    "Id": "o-exampleorgid",
                    "Type": "ORGANIZATION"
                },
                {
                    "Id": "susan@example.com",
                    "Type": "EMAIL"
                }
            ],
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
                        },
                        {
                            "Type": "ORGANIZATION_FEATURE_SET",
                            "Value": "CONSOLIDATED_BILLING"
                        }
                    ]
                },
                {
                    "Type": "EMAIL",
                    "Value": "anika@example.com"
                },
                {
                    "Type": "NOTES",
                    "Value": "This is a request for Susan's account to join Bob's organization."
                }
            ],
            "RequestedTimestamp": 1.47008383521E9,
            "ExpirationTimestamp": 1.47137983521E9
        }
    }

For more information, see `Managing pending account invitations with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_manage-invites.html>`__ in the *AWS Organizations User Guide*.
