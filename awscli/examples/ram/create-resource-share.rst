**Example 1: To create a resource share**

The following ``create-resource-share`` example creates a resource share with the specified name. ::

    aws ram create-resource-share \
        --name my-resource-share 

Output::

    {
        "resourceShare": {
            "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/7ab63972-b505-7e2a-420d-6f5d3EXAMPLE",
            "name": "my-resource-share",
            "owningAccountId": "123456789012",
            "allowExternalPrincipals": true,
            "status": "ACTIVE",
            "creationTime": 1565295733.282,
            "lastUpdatedTime": 1565295733.282
        }
    }

**Example 2: To create a resource share with AWS accounts as principals**

The following ``create-resource-share`` example creates a resource share and adds the specified principals. ::

    aws ram create-resource-share \
        --name my-resource-share \
        --principals 0abcdef1234567890

**EXAMPLE 3: To create a resource share restricted to your organization in AWS Organizations**

The following ``create-resource-share`` example creates a resource share that is restricted to your organization and adds the specified OU as a principal. ::

    aws ram create-resource-share \
        --name my-resource-share \
        --no-allow-external-principals \
        --principals arn:aws:organizations::123456789012:ou/o-gx7EXAMPLE/ou-29c5-zEXAMPLE 

Output::

    {
        "resourceShare": {
            "resourceShareArn": "arn:aws:ram:us-west-2:123456789012:resource-share/3ab63985-99d9-1cd2-7d24-75e93EXAMPLE",
            "name": "my-resource-share",
            "owningAccountId": "123456789012",
            "allowExternalPrincipals": false,
            "status": "ACTIVE",
            "creationTime": 1565295733.282,
            "lastUpdatedTime": 1565295733.282
        }
    }
