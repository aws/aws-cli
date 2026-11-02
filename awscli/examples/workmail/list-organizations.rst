**To retrieve a list of organizations**

The following ``list-organizations`` example retrieves summaries of the customer's organizations. ::

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

For more information, see `Working with organizations <https://docs.aws.amazon.com/workmail/latest/adminguide/organizations_overview.html>`__ in the *Amazon WorkMail Administrator Guide*.
