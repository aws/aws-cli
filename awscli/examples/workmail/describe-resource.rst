**To retrieve information for a resource**

This example retrieves information for a specified resource.

Command::

  aws workmail describe-resource --organization-id m-d281d0a2fd824be5b6cd3d3ce909fd27 --resource-id r-7afe0efbade843a58cdc10251fce992c

Output::

  {
    "ResourceId": "r-7afe0efbade843a58cdc10251fce992c",
    "Name": "exampleRoom1",
    "Type": "ROOM",
    "BookingOptions": {
        "AutoAcceptRequests": true,
        "AutoDeclineRecurringRequests": false,
        "AutoDeclineConflictingRequests": true
    },
    "State": "ENABLED"
  }