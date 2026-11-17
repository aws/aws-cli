**To enable all features in an organization**

The following ``enable-all-features`` example asks all the invited accounts in the organization to approve enabling all features in the organization. AWS Organizations sends an email to the address that is registered with every invited member account asking the owner to approve the change to all features by accepting the handshake that is sent. After all invited member accounts accept the handshake, the organization administrator can finalize the change to all features, and those with appropriate permissions can create policies and apply them to roots, OUs, and accounts. ::

    aws organizations enable-all-features

The output is a handshake object that is sent to all invited member accounts for approval.

Output::

    {
        "Handshake": {
            "Action": "ENABLE_ALL_FEATURES",
            "Arn": "arn:aws:organizations::123456789012:handshake/o-exampleorgid/enable_all_features/h-examplehandshakeid111",
            "ExpirationTimestamp": 1483127868.609,
            "Id": "h-examplehandshakeid111",
            "Parties": [
                {
                    "Id": "o-exampleorgid",
                    "Type": "ORGANIZATION"
                }
            ],
            "RequestedTimestamp": 1481831868.609,
            "Resources": [
                {
                    "Type": "ORGANIZATION",
                    "Value": "o-exampleorgid"
                }
            ],
            "State": "REQUESTED"
        }
    }

For more information, see `Enabling all features for an organization with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_org_support-all-features.html>`__ in the *AWS Organizations User Guide*.
