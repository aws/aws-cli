**To get the per-region base path mapping for a custom domain name**

Command::

  aws apigateway get-base-path-mappings --domain-name subdomain.domain.tld --region us-west-2

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

