**To get the per-region base path mapping for a custom domain name**

Command::

  aws apigateway get-base-path-mapping --domain-name subdomain.domain.tld --base-path v1 --region us-west-2

Output::

  {
      "basePath": "v1", 
      "restApiId": "1234w4321e", 
      "stage": "api"
  }

