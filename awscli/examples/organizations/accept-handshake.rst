**To accept a handshake from another account**

The following ``accept-handshake`` example accepts a handshake on behalf of Juan's account and thus agrees to the invitation. Bill, the owner of an organization, has previously invited Juan's account to join his organization. ::

    aws organizations accept-handshake \
        --handshake-id h-examplehandshakeid111

Output::

    {
        "Handshake": {
            "Action": "INVITE",
            "Arn": "arn:aws:organizations::123456789012:handshake/o-exampleorgid/invite/h-examplehandshakeid111",
            "RequestedTimestamp": 1481656459.257,
            "ExpirationTimestamp": 1482952459.257,
            "Id": "h-examplehandshakeid111",
            "Parties": [
                {
                    "Id": "o-exampleorgid",
                    "Type": "ORGANIZATION"
                },
                {
                    "Id": "juan@example.com",
                    "Type": "EMAIL"
                }
            ],
            "Resources": [
                {
                    "Resources": [
                        {
                            "Type": "MASTER_EMAIL",
                            "Value": "bill@amazon.com"
                        },
                        {
                            "Type": "MASTER_NAME",
                            "Value": "Org Master Account"
                        },
                        {
                            "Type": "ORGANIZATION_FEATURE_SET",
                            "Value": "ALL"
                        }
                    ],
                    "Type": "ORGANIZATION",
                    "Value": "o-exampleorgid"
                },
                {
                    "Type": "EMAIL",
                    "Value": "juan@example.com"
                }
            ],
            "State": "ACCEPTED"
        }
    }

For more information, see `Accepting or declining account invitations with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_accounts_accept-decline-invite.html>`__ in the *AWS Organizations User Guide*.
