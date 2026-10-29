**To retrieve a list of groups**

The following ``describe-groups`` example lists the groups associated with the specified Amazon WorkDocs organization. ::

    aws workdocs describe-groups \
        --search-query "e" \
        --organization-id d-123456789c

Output::

    {
        "Groups": [
            {
                "Id": "S-1-1-11-1122222222-2222233333-3333334444-4444&d-123456789c",
                "Name": "Example Group 1"
            },
            {
                "Id": "S-1-1-11-1122222222-2222233333-3333334444-5555&d-123456789c",
                "Name": "Example Group 2"
            }
        ]
    }
