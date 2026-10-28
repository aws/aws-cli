**To delete a base path mapping for a custom domain name**

The following ``delete-base-path-mapping`` example deletes a base path mapping for a custom domain name. ::

    aws apigateway delete-base-path-mapping \
        --domain-name 'api.domain.tld' \
        --base-path 'dev'
