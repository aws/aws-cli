**To create a new resource**

This example creates a new resource (meeting room) for the specified organization.

Command::

  aws workmail create-resource --organization-id m-d281d0a2fd824be5b6cd3d3ce909fd27 --name exampleRoom1 --type ROOM

Output::

  {
    "ResourceId": "r-7afe0efbade843a58cdc10251fce992c"
  }