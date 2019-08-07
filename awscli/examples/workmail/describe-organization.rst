**To retrieve information for an organization**

The following ``describe-organization`` command retrieves information for the specified Amazon WorkMail organization. ::

    aws workmail describe-organization \
        --organization-id m-d281d0a2fd824be5b6cd3d3ce909fd27

Output::

    {
        "OrganizationId": "m-d281d0a2fd824be5b6cd3d3ce909fd27",
        "Alias": "alias",
        "State": "Active",
        "DirectoryId": "d-926726012c",
        "DirectoryType": "VpcDirectory",
        "DefaultMailDomain": "site.awsapps.com",
        "CompletedDate": 1522693605.468
    }
