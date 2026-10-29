**To list connections**

The following ``list-connections`` example retrieves a list of all connections in your account for the Bitbucket provider type. ::

    aws codestar-connections list-connections \
        --provider-type Bitbucket \
        --max-results 5 \
        --next-token next-token

Output::

    {
        "Connections": [
            {
                "ConnectionName": "my-connection",
                "ProviderType": "Bitbucket",
                "ConnectionStatus": "PENDING",
                "ConnectionArn": "arn:aws:codestar-connections:us-west-2:123456789012:connection/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "OwnerAccountId": "123456789012"
            },
            {
                "ConnectionName": "my-other-connection",
                "ProviderType": "Bitbucket",
                "ConnectionStatus": "AVAILABLE",
                "ConnectionArn": "arn:aws:codestar-connections:us-west-2:123456789012:connection/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "OwnerAccountId": "123456789012"
            }
        ],
        "NextToken": "next-token"
    }

For more information, see `List connections (CLI) <https://docs.aws.amazon.com/dtconsole/latest/userguide/connections-list.html#connections-list-cli>`__ in the *Developer Tools console User Guide*.