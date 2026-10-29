**To get the base path mappings for a custom domain name**

The following ``get-base-path-mappings`` example gets the base path mappings for the custom domain name ``subdomain.domain.tld``. ::

    aws apigateway get-base-path-mappings \
        --domain-name subdomain.domain.tld

Output::

    {
        "items": [
            {
                "basePath": "(none)",
                "restApiId": "1234w4321e",
                "stage": "dev"
            },
            {
                "basePath": "v1",
                "restApiId": "1234w4321e",
                "stage": "api"
            }
        ]
    }

For more information, see `Use API mappings to connect API stages to a custom domain name for REST APIs <https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-mappings.html>`__ in the *Amazon API Gateway Developer Guide*.
