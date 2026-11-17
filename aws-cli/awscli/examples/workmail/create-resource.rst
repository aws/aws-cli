**To create a new resource**

The following ``create-resource`` example creates a new resource (meeting room) for the specified organization. ::

    aws workmail create-resource \
        --organization-id m-d281d0a2fd824be5b6cd3d3ce909fd27 \
        --name exampleRoom1 \
        --type ROOM

Output::

    {
        "ResourceId": "r-7afe0efbade843a58cdc10251fce992c"
    }

For more information, see `Adding a resource <https://docs.aws.amazon.com/workmail/latest/adminguide/create_resource.html>`__ in the *Amazon WorkMail Administrator Guide*.
