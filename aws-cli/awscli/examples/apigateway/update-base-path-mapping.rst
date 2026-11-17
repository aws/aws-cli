**To change the base path for a custom domain name**

The following ``update-base-path-mapping`` example changes the base path for a custom domain name. ::

    aws apigateway update-base-path-mapping \
        --domain-name api.domain.tld \
        --base-path prod \
        --patch-operations op='replace',path='/basePath',value='v1'

Output::

    {
        "basePath": "v1",
        "restApiId": "1234123412",
        "stage": "api"
    }

For more information, see `Use API mappings to connect API stages to a custom domain name for REST APIs <https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-mappings.html>`__ in the *Amazon API Gateway Developer Guide*.
