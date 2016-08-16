**To change the certificate name for a custom domain name**

Command::

  aws apigateway update-domain-name --domain-name api.domain.tld --patch-operations op='replace',path='/certificateName',value='newDomainCertName'

Output::

  {
      "domainName": "api.domain.tld", 
      "distributionDomainName": "d123456789012.cloudfront.net", 
      "certificateName": "newDomainCertName", 
      "certificateUploadDate": 1462565487
  }

