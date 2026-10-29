**To get the base path mapping for a custom domain name**

The following ``get-base-path-mapping`` example gets the base path mapping for a custom domain name. ::

    aws apigateway get-base-path-mapping \
        --domain-name subdomain.domain.tld \
        --base-path v1

Output::

    {
        "basePath": "v1",
        "restApiId": "1234w4321e",
        "stage": "api"
    }

For more information, see `Use API mappings to connect API stages to a custom domain name for REST APIs <https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-mappings.html>`__ in the *Amazon API Gateway Developer Guide*.
