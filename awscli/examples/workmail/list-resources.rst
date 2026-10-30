**To retrieve a list of resources**

The following ``list-resources`` example retrieves summaries of the resources for the specified organization. ::

    aws workmail list-resources \
        --organization-id m-d281d0a2fd824be5b6cd3d3ce909fd27

Output::

    {
        "Resources": [
            {
                "Id": "r-7afe0efbade843a58cdc10251fce992c",
                "Name": "exampleRoom1",
                "Type": "ROOM",
                "State": "ENABLED"
            }
        ]
    }

For more information, see `Viewing a list of resources <https://docs.aws.amazon.com/workmail/latest/adminguide/display_resource.html>`__ in the *Amazon WorkMail Administrator Guide*.
