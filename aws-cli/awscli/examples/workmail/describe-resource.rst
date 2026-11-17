**To retrieve information for a resource**

The following ``describe-resource`` example retrieves information about the specified resource. ::

    aws workmail describe-resource \
        --organization-id m-d281d0a2fd824be5b6cd3d3ce909fd27 \
        --resource-id r-7afe0efbade843a58cdc10251fce992c

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

For more information, see `Working with resources <https://docs.aws.amazon.com/workmail/latest/adminguide/resources_overview.html>`__ in the *Amazon WorkMail Administrator Guide*.
