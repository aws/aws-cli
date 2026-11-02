**To get an authorization token for your default registry**

The following ``get-authorization-token`` example command gets an authorization token for your default registry. ::

    aws ecr get-authorization-token

Output::

    {
        "authorizationData": [
            {
                "authorizationToken": "QVdTOkN...",
                "expiresAt": 1448875853.241,
                "proxyEndpoint": "https://123456789012.dkr.ecr.us-west-2.amazonaws.com"
            }
        ]
    }

For more information, see `Private registry authentication in Amazon ECR <https://docs.aws.amazon.com/AmazonECR/latest/userguide/registry_auth.html>`__ in the *Amazon ECR User Guide*.
