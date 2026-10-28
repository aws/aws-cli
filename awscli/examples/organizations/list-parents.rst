**To list the parent OUs or roots for an account or child OU**

The following ``list-parents`` example lists the root or parent OU that contains the account 444444444444. ::

    aws organizations list-parents \
        --child-id 444444444444

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
