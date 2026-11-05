**To delete a base path mapping for a custom domain name**

The following ``delete-base-path-mapping`` example deletes a base path mapping for a custom domain name. ::

    aws apigateway delete-base-path-mapping \
        --domain-name 'api.domain.tld' \
        --base-path 'dev'

This command produces no output.

For more information, see `Use API mappings to connect API stages to a custom domain name for REST APIs <https://docs.aws.amazon.com/apigateway/latest/developerguide/rest-api-mappings.html>`__ in the *Amazon API Gateway Developer Guide*.
