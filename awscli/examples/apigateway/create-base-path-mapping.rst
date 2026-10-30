**To create the base path mapping for a custom domain name**

The following ``create-base-path-mapping`` example creates the base path mapping for a custom domain name. ::

    aws apigateway create-base-path-mapping \
        --domain-name subdomain.domain.tld \
        --rest-api-id 1234123412 \
        --stage prod \
        --base-path v1

Output::

    {
        "basePath": "v1",
        "restApiId": "1234123412",
        "stage": "prod"
    }

For more information, see `Custom domain name for public REST APIs in API Gateway <https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-custom-domains.html>`__ in the *Amazon API Gateway Developer Guide*.
