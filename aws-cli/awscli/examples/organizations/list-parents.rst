**To list the parent OUs or roots for an account or child OU**

The following ``list-parents`` example lists the root or parent OU that contains the account 444444444444. ::

    aws organizations list-parents \
        --child-id 123456789333

The output shows that the specified account is in the OU with specified ID.

Output::

    {
        "Parents": [
            {
                "Id": "ou-examplerootid111-exampleouid111",
                "Type": "ORGANIZATIONAL_UNIT"
            }
        ]
    }

For more information, see `Managing organizational units (OUs) with AWS Organizations <https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_ous.html>`__ in the *AWS Organizations User Guide*.
