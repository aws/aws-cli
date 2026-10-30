**To retrieve a list of the roots, OUs, and accounts that a policy is attached to**

The following ``list-targets-for-policy`` example gets a list of the roots, OUs, and accounts that the specified policy is attached to. The output includes a list of attachment objects with summary information about the roots, OUs, and accounts the policy is attached to. ::

    aws organizations list-targets-for-policy \
        --policy-id p-FullAWSAccess

Output::

    {
        "Targets": [
            {
                "Arn": "arn:aws:organizations::123456789012:root/o-exampleorgid/r-examplerootid111",
                "Name": "Root",
                "TargetId": "r-examplerootid111",
                "Type": "ROOT"
            },
            {
                "Arn": "arn:aws:organizations::123456789012:account/o-exampleorgid/123456789222",
                "Name": "Developer Test Account",
                "TargetId": "123456789222",
                "Type": "ACCOUNT"
            },
            {
                "Arn": "arn:aws:organizations::123456789012:ou/o-exampleorgid/ou-examplerootid111-exampleouid111",
                "Name": "Accounting",
                "TargetId": "ou-examplerootid111-exampleouid111",
                "Type": "ORGANIZATIONAL_UNIT"
            }
        ]
    }

For more information, see `Getting information about your organization's policies <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_info-operations.html>`__ in the *AWS Organizations User Guide*.
