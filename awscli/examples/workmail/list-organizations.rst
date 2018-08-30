**To retrieve a list of organizations**

This example retrieves summaries of non-deleted organizations.

Command::

  aws workmail list-organizations

Output::

  {
    "OrganizationSummaries": [
        {
            "OrganizationId": "m-d281d0a2fd824be5b6cd3d3ce909fd27",
            "Alias": "exampleAlias",
            "State": "Active"
        }
    ]
  }