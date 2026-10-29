**To get information about a connection**

The following ``get-connection`` example shows details about a connection. ::

    aws codestar-connections get-connection \
        --connection-arn arn:aws:codestar-connections:us-west-2:123456789012:connection/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

Output::

    {
        "Connection": {
            "ConnectionName": "MyConnection",
            "ConnectionArn": "arn:aws:codestar-connections:us-west-2:123456789012:connection/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "ProviderType": "Bitbucket",
            "OwnerAccountId": "123456789012",
            "ConnectionStatus": "AVAILABLE"
        }
    }

For more information, see `View connection details <https://docs.aws.amazon.com/dtconsole/latest/userguide/connections-view-details.html>`__ in the *Developer Tools console User Guide*.